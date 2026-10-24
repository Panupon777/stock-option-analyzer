from fastapi import FastAPI, Depends, HTTPException, status, Header
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import httpx
import json

from config import settings
from database import get_db, create_tables, User, Subscription, SubscriptionStatus, AnalysisHistory, DailyUsage, FlashSale, UserRole
from auth import hash_password, verify_password, create_access_token, verify_token, get_current_user, verify_admin_password
from schemas import (
    UserRegisterRequest, UserLoginRequest, UserResponse, AuthResponse, MeResponse,
    SubscriptionRequest, SubscriptionResponse, SubscriptionStatus as SubscriptionStatusSchema,
    SubscriptionItem, AnalyzeRequest, AnalysisResponse, HealthResponse,
    ScannerCategory, ScannerResults, ScanResult, FlashSaleResponse,
    FlashSaleCreateRequest, FlashSaleSetResponse, ApproveSubscriptionResponse
)
import finnhub_client
from probability import generate_option_levels, calc_probability

# Initialize
app = FastAPI(title="Stock Option Analyzer API")
create_tables()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ═══════════════════════
# HEALTH CHECK
# ═══════════════════════
@app.get("/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse(
        status="ok",
        anthropic=bool(settings.anthropic_api_key),
        finnhub=bool(settings.finnhub_api_key),
    )


# ═══════════════════════
# AUTH ROUTES
# ═══════════════════════
@app.post("/api/auth/register", response_model=AuthResponse)
async def register(req: UserRegisterRequest, db: Session = Depends(get_db)):
    # Check if email exists
    existing = db.query(User).filter(User.email == req.email).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This email is already registered")

    # Hash password and create user
    hashed = hash_password(req.password)
    user = User(
        email=req.email,
        password_hash=hashed,
        name=req.name,
        role=UserRole.free,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(user.id)
    return AuthResponse(
        token=token,
        user=UserResponse(id=user.id, email=user.email, name=user.name, role=user.role.value),
    )


@app.post("/api/auth/login", response_model=AuthResponse)
async def login(req: UserLoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Account not found")

    if not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Incorrect password")

    token = create_access_token(user.id)
    return AuthResponse(
        token=token,
        user=UserResponse(id=user.id, email=user.email, name=user.name, role=user.role.value),
    )


@app.get("/api/auth/me", response_model=MeResponse)
async def get_me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    today = datetime.utcnow().strftime("%Y-%m-%d")
    usage = db.query(DailyUsage).filter(
        DailyUsage.user_id == current_user.id,
        DailyUsage.date == today,
    ).first()

    usage_count = usage.count if usage else 0
    return MeResponse(
        user=UserResponse(id=current_user.id, email=current_user.email, name=current_user.name, role=current_user.role.value),
        usage_today=usage_count,
    )


# ═══════════════════════
# SUBSCRIPTION ROUTES
# ═══════════════════════
@app.post("/api/subscribe/request", response_model=SubscriptionResponse)
async def subscribe_request(req: SubscriptionRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Get active flash sale
    active_sale = db.query(FlashSale).filter(
        FlashSale.is_active == True,
        FlashSale.ends_at > datetime.utcnow(),
    ).first()

    price = active_sale.sale_price if active_sale else settings.subscription_price

    # Create subscription record
    sub = Subscription(
        user_id=current_user.id,
        status=SubscriptionStatus.pending,
        plan="pro",
        amount=price,
        slip_note=req.slip_note or "",
    )
    db.add(sub)
    db.commit()

    return SubscriptionResponse(
        success=True,
        promptpay=settings.promptpay_number,
        amount=price,
        original_price=settings.subscription_price if active_sale else None,
        is_flash_sale=bool(active_sale),
        sale_label=active_sale.label if active_sale else None,
        message=f"Transfer {price} THB to PromptPay {settings.promptpay_number}",
    )


@app.get("/api/subscribe/status", response_model=SubscriptionStatusSchema)
async def subscribe_status(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    latest_sub = db.query(Subscription).filter(
        Subscription.user_id == current_user.id,
    ).order_by(Subscription.created_at.desc()).first()

    return SubscriptionStatusSchema(
        subscription={"id": latest_sub.id, "status": latest_sub.status.value, "amount": latest_sub.amount, "slip_note": latest_sub.slip_note, "expires_at": latest_sub.expires_at, "created_at": latest_sub.created_at} if latest_sub else None,
        promptpay=settings.promptpay_number,
        amount=settings.subscription_price,
        role=current_user.role.value,
    )


@app.get("/api/admin/subscriptions")
async def get_pending_subscriptions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    x_admin_password: bool = Depends(verify_admin_password),
):
    pending = db.query(Subscription).filter(
        Subscription.status == SubscriptionStatus.pending,
    ).order_by(Subscription.created_at.desc()).all()

    result = []
    for sub in pending:
        user = db.query(User).filter(User.id == sub.user_id).first()
        result.append({
            "id": sub.id,
            "user_id": sub.user_id,
            "email": user.email if user else "",
            "name": user.name if user else "",
            "amount": sub.amount,
            "slip_note": sub.slip_note,
            "status": sub.status.value,
            "created_at": sub.created_at.isoformat(),
        })

    return result


@app.post("/api/admin/approve/{sub_id}")
async def approve_subscription(
    sub_id: int,
    db: Session = Depends(get_db),
    x_admin_password: bool = Depends(verify_admin_password),
):
    sub = db.query(Subscription).filter(Subscription.id == sub_id).first()
    if not sub:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    expires = datetime.utcnow() + timedelta(days=30)
    sub.status = SubscriptionStatus.approved
    sub.approved_at = datetime.utcnow()
    sub.expires_at = expires

    user = db.query(User).filter(User.id == sub.user_id).first()
    if user:
        user.role = UserRole.pro

    db.commit()

    return ApproveSubscriptionResponse(
        success=True,
        message=f"Approved — Pro until {expires.strftime('%Y-%m-%d')}",
    )


# ═══════════════════════
# ANALYSIS ROUTE
# ═══════════════════════
def check_usage_limit(current_user: User, db: Session):
    if current_user.role == UserRole.pro:
        return True

    today = datetime.utcnow().strftime("%Y-%m-%d")
    usage = db.query(DailyUsage).filter(
        DailyUsage.user_id == current_user.id,
        DailyUsage.date == today,
    ).first()

    count = usage.count if usage else 0
    if count >= 3:
        return False
    return True


@app.post("/api/analyze")
async def analyze(
    req: AnalyzeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not check_usage_limit(current_user, db):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Daily limit reached",
            headers={"X-Upgrade": "true"},
        )

    if not settings.anthropic_api_key:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="ANTHROPIC_API_KEY not configured")

    # Fetch Finnhub data
    try:
        stock_data = await finnhub_client.fetch_all_data(req.ticker)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    cp = stock_data["quote"]["current_price"]
    profile = stock_data.get("profile") or {}
    news = stock_data.get("news") or []
    recs = stock_data.get("recommendations")
    sentiment = stock_data.get("sentiment")
    earnings = stock_data.get("upcoming_earnings")

    # Map horizon
    horizon_map = {
        "weekly": {"days": 13, "label": "1-2 weeks"},
        "month1": {"days": 30, "label": "1 month"},
        "month2": {"days": 60, "label": "2 months"},
        "month3": {"days": 90, "label": "3 months"},
        "monthly": {"days": 30, "label": "1 month"},
    }
    h = horizon_map.get(req.horizon, horizon_map["weekly"])
    horizon_label = h["label"]
    days_left = h["days"]

    # Build context for Claude
    context = f"\n\n═══ STOCK DATA (Finnhub real-time, fetched {stock_data['fetched_at_label']}) ═══"
    if profile.get("name"):
        context += f"\n📊 Company: {profile['name']} ({profile.get('exchange', '')}) — {profile.get('industry', 'N/A')}"
    context += f"\n💵 Price: ${cp} | Change: {stock_data['quote']['change_pct']:.2f}% | High: ${stock_data['quote']['day_high']} | Low: ${stock_data['quote']['day_low']}"
    if profile.get("market_cap"):
        context += f"\n🏦 Market Cap: ${profile['market_cap']/1000:.2f}B"

    if recs:
        context += f"\n📈 Analyst ({recs['period']}): Strong Buy {recs['strong_buy']}, Buy {recs['buy']}, Hold {recs['hold']}, Sell {recs['sell']}, Strong Sell {recs['strong_sell']}"

    if sentiment:
        context += f"\n📰 News Sentiment: buzz={sentiment['buzz']}, score={sentiment['company_news_score']}"

    if earnings:
        context += f"\n📅 Upcoming Earnings: {earnings['date']} ({earnings['hour']})"

    if news:
        context += f"\n\n═══ RECENT NEWS ({len(news)} items) ═══"
        for i, n in enumerate(news[:8]):
            context += f"\n{i+1}. [{n['published_label']}] {n['title']} ({n['publisher']})"
            if n.get("summary"):
                context += f"\n   {n['summary'][:150]}"

    model = "claude-opus-4-5" if current_user.role == UserRole.pro else "claude-haiku-4-5-20251001"

    prompt = f"""You are a professional stock and options analyst. Analyze {req.ticker} for {horizon_label} options trading using the REAL-TIME data below.{context}

Reply ONLY with JSON (no markdown, strings under 100 chars except "callExplanation" and "putExplanation" which can be 200 chars):
{{"ticker":"{req.ticker}","market":"{req.market or 'US'}","horizon":"{horizon_label}","currentPrice":{cp},"priceTarget":0,"direction":"BULLISH","confidence":70,"summaryTH":"Two-sentence English summary based on the real news above","optionStrategy":{{"recommended":"CALL","strike":"ATM","expiry":"{days_left} days","rationale":"Brief rationale in English"}},"callExplanation":"Explain in plain English why trading CALL now is advisable or not, using the real news and data above. Start with ✅ if recommended or ❌ otherwise, with 2-3 reasons","putExplanation":"Explain in plain English why trading PUT now is advisable or not, with 2-3 reasons. Start with ✅ or ❌","sentimentScores":{{"newsSentiment":50,"socialSentiment":30,"analystRating":40}},"factors":[{{"name":"Earnings","score":60,"detail":"brief"}},{{"name":"Macro","score":40,"detail":"brief"}},{{"name":"Sector","score":50,"detail":"brief"}},{{"name":"Technical","score":55,"detail":"brief"}},{{"name":"Catalyst","score":45,"detail":"brief"}},{{"name":"Risk","score":-30,"detail":"brief"}}],"keyNews":[{{"headline":"From real news","impact":"POSITIVE","date":"date","detail":"brief"}},{{"headline":"From real news","impact":"NEGATIVE","date":"date","detail":"brief"}},{{"headline":"From real news","impact":"NEUTRAL","date":"date","detail":"brief"}}],"priceScenarios":{{"bull":0,"base":0,"bear":0}},"estimatedIV":0.5}}"""

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "Content-Type": "application/json",
                    "x-api-key": settings.anthropic_api_key,
                    "anthropic-version": "2023-06-01",
                },
                json={
                    "model": model,
                    "max_tokens": 2000,
                    "messages": [{"role": "user", "content": prompt}],
                },
                timeout=30.0,
            )

            if response.status_code != 200:
                raise HTTPException(status_code=response.status_code, detail="Anthropic API error")

            data = response.json()
            full_text = "".join([b["text"] for b in data["content"] if b["type"] == "text"])

            start = full_text.find("{")
            end = full_text.rfind("}") + 1
            if start == -1 or end == 0:
                raise HTTPException(status_code=500, detail="Parse failed")

            result = json.loads(full_text[start:end])

            # Add option levels
            iv = result.get("estimatedIV", 0.5)
            direction = result.get("direction", "BULLISH")
            dir_val = "UP" if direction == "BULLISH" else "DOWN"
            result["option_levels"] = generate_option_levels(cp, iv, days_left, dir_val)
            result["days_left"] = days_left
            result["stock_data"] = stock_data
            result["model_used"] = f"Claude Opus (Pro)" if current_user.role == UserRole.pro else "Claude Haiku (Free)"

            # Increment usage
            today = datetime.utcnow().strftime("%Y-%m-%d")
            usage = db.query(DailyUsage).filter(
                DailyUsage.user_id == current_user.id,
                DailyUsage.date == today,
            ).first()

            if usage:
                usage.count += 1
            else:
                usage = DailyUsage(user_id=current_user.id, date=today, count=1)
                db.add(usage)

            # Add to history
            history = AnalysisHistory(
                user_id=current_user.id,
                ticker=req.ticker,
                market=req.market or "US",
                direction=result.get("direction"),
                confidence=result.get("confidence"),
                result=result,
            )
            db.add(history)
            db.commit()

            return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/history")
async def get_history(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    history = db.query(AnalysisHistory).filter(
        AnalysisHistory.user_id == current_user.id,
    ).order_by(AnalysisHistory.created_at.desc()).limit(20).all()

    return [
        {
            "id": h.id,
            "ticker": h.ticker,
            "market": h.market,
            "direction": h.direction,
            "confidence": h.confidence,
            "result": h.result,
            "created_at": h.created_at.isoformat(),
        }
        for h in history
    ]


# ═══════════════════════
# FLASH SALE ROUTES
# ═══════════════════════
@app.get("/api/flashsale")
async def get_flash_sale(db: Session = Depends(get_db)):
    sale = db.query(FlashSale).filter(
        FlashSale.is_active == True,
        FlashSale.ends_at > datetime.utcnow(),
    ).first()

    if not sale:
        return None

    return {
        "original_price": sale.original_price,
        "sale_price": sale.sale_price,
        "discount_pct": sale.discount_pct,
        "label": sale.label,
        "ends_at": sale.ends_at.isoformat(),
        "started_at": sale.started_at.isoformat(),
    }


@app.post("/api/admin/flashsale", response_model=FlashSaleSetResponse)
async def set_flash_sale(
    req: FlashSaleCreateRequest,
    db: Session = Depends(get_db),
    x_admin_password: bool = Depends(verify_admin_password),
):
    # Deactivate old sales
    db.query(FlashSale).update({"is_active": False})

    ends_at = datetime.utcnow() + timedelta(minutes=req.duration_minutes)
    sale = FlashSale(
        original_price=req.price,
        sale_price=int(req.price * (1 - req.discount_pct / 100)),
        discount_pct=req.discount_pct,
        label=req.label,
        ends_at=ends_at,
        is_active=True,
    )
    db.add(sale)
    db.commit()
    db.refresh(sale)

    return FlashSaleSetResponse(
        success=True,
        sale=FlashSaleResponse(
            original_price=sale.original_price,
            sale_price=sale.sale_price,
            discount_pct=sale.discount_pct,
            label=sale.label,
            ends_at=sale.ends_at,
            started_at=sale.started_at,
        ),
    )


@app.delete("/api/admin/flashsale")
async def delete_flash_sale(
    db: Session = Depends(get_db),
    x_admin_password: bool = Depends(verify_admin_password),
):
    db.query(FlashSale).update({"is_active": False})
    db.commit()
    return {"success": True, "message": "Flash sale has been canceled"}


# ═══════════════════════
# GLOSSARY ROUTE
# ═══════════════════════
from glossary import GLOSSARY_DATA


@app.get("/api/glossary")
async def get_glossary():
    return GLOSSARY_DATA


# ═══════════════════════
# SCANNER ROUTES
# ═══════════════════════
from scanner import WATCHLISTS, scan_watchlist, estimate_option_cost, score_stock


@app.get("/api/scanner/categories")
async def get_scanner_categories(current_user: User = Depends(get_current_user)):
    categories = []
    for key, data in WATCHLISTS.items():
        categories.append({
            "key": key,
            "label": data["label"],
            "count": len(data["tickers"]),
            "tier": data["tier"],
            "description": data.get("description"),
            "locked": data["tier"] == "pro" and current_user.role != UserRole.pro,
        })
    return categories


@app.post("/api/scanner/scan")
async def scan_category(
    req: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    category = req.get("category")
    if not category:
        raise HTTPException(status_code=400, detail="category required")

    watchlist = WATCHLISTS.get(category)
    if not watchlist:
        raise HTTPException(status_code=404, detail=f"Unknown category: {category}")

    if watchlist["tier"] == "pro" and current_user.role != UserRole.pro:
        raise HTTPException(status_code=403, detail="PRO_REQUIRED")

    try:
        results = await scan_watchlist(category, current_user.role.value)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=settings.port)
