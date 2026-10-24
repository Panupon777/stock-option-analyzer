from datetime import datetime
import finnhub_client
from probability import calc_probability, generate_option_levels


WATCHLISTS = {
    # ── FREE ──────────────────────────────────────
    "popular": {
        "label": "🔥 Popular stocks",
        "tier": "free",
        "tickers": ["NVDA", "AAPL", "TSLA", "META", "AMZN", "MSFT", "GOOGL", "AMD", "NFLX", "PLTR"],
    },
    "smallcap": {
        "label": "🚀 Small-cap stocks",
        "tier": "free",
        "tickers": ["IONQ", "OKLO", "NNE", "SOUN", "AEHR", "EOSE", "LUNR", "RKLB", "RGTI", "QUBT"],
    },
    "earnings": {
        "label": "📅 Earnings watchlist",
        "tier": "free",
        "tickers": ["NVDA", "AAPL", "TSLA", "META", "AMZN", "GOOGL", "NFLX", "AMD", "CRWD", "SNOW"],
    },

    # ── PRO เท่านั้น ──────────────────────────────
    "hidden_gems": {
        "label": "💎 Hidden gems",
        "tier": "pro",
        "description": "Lesser-known stocks with potential news catalysts.",
        "tickers": ["BTBT", "CIFR", "ARBK", "MARA", "RIOT", "CLSK", "WULF", "IREN", "CORZ", "HUT"],
    },
    "budget_options": {
        "label": "💰 Budget options watchlist",
        "tier": "pro",
        "description": "Watchlist for exploring lower-cost options. Actual premiums vary by contract.",
        "tickers": ["SOFI", "PLUG", "FCEL", "BLNK", "CHPT", "OPEN", "CLOV", "SENS", "GOEV", "WKHS"],
    },
    "news_movers": {
        "label": "📰 News movers (Meme + Speculative)",
        "tier": "pro",
        "description": "Stocks that may react strongly to news.",
        "tickers": ["GME", "AMC", "SPCE", "LCID", "RIVN", "FFIE", "MULN", "BBAI", "PRCT", "MAPS"],
    },
    "biotech": {
        "label": "🧬 Biotech FDA catalyst",
        "tier": "pro",
        "description": "Event-driven watchlist with elevated risk.",
        "tickers": ["ACHR", "JOBY", "NVAX", "SRPT", "SAGE", "BEAM", "EDIT", "NTLA", "CRSP", "PACB"],
    },
    "ai_chip": {
        "label": "🤖 AI & Semiconductor",
        "tier": "pro",
        "tickers": ["NVDA", "AMD", "AVGO", "TSM", "ARM", "SMCI", "MRVL", "NVTS", "CRDO", "ALAB"],
    },
    "nuclear": {
        "label": "⚛️ Nuclear & Clean Energy",
        "tier": "pro",
        "tickers": ["OKLO", "NNE", "SMR", "LEU", "CCJ", "BWXT", "VST", "CEG", "TLN", "GEV"],
    },
}


def estimate_option_cost(price: float) -> dict:
    """Estimate option cost tier"""
    if not price or price <= 0:
        return {"label": "—", "cost": "N/A", "tier": "unknown"}

    premium = price * 0.05
    per_contract = premium * 100

    if per_contract < 50:
        return {"label": "🟢 Very low cost", "cost": f"~${int(per_contract)}", "tier": "budget", "badge": "<$50"}
    elif per_contract < 150:
        return {"label": "🟡 Low cost", "cost": f"~${int(per_contract)}", "tier": "cheap", "badge": "<$150"}
    elif per_contract < 400:
        return {"label": "🟠 Moderate", "cost": f"~${int(per_contract)}", "tier": "mid", "badge": "<$400"}
    else:
        return {"label": "🔴 High cost", "cost": f"~${int(per_contract/100)*100}+", "tier": "expensive", "badge": "$400+"}


def score_stock(data: dict) -> dict:
    """Score stock for scanner"""
    score = 0
    reasons = []
    direction = "NEUTRAL"

    change_pct = data.get("quote", {}).get("change_pct", 0)
    change = change_pct

    # 1. Movement
    if abs(change_pct) > 8:
        score += 30
        reasons.append(f"🔥 Large move {change:.1f}%")
    elif abs(change_pct) > 5:
        score += 20
        reasons.append(f"📊 Strong move {change:.1f}%")
    elif abs(change_pct) > 2:
        score += 10
        reasons.append(f"📊 Move {change:.1f}%")

    # 2. Direction
    if change > 2:
        direction = "BULLISH"
    elif change < -2:
        direction = "BEARISH"

    # 3. News
    news_items = data.get("news", [])
    recent_news = [n for n in news_items if n.get("is_stale") is False]
    if len(recent_news) >= 5:
        score += 25
        reasons.append(f"📰 {len(recent_news)} recent news items / 48h")
    elif len(recent_news) >= 2:
        score += 12
        reasons.append(f"📰 {len(recent_news)} recent news items")

    # 4. Analyst
    recs = data.get("recommendations")
    if recs:
        bull = (recs.get("strong_buy", 0) or 0) * 2 + (recs.get("buy", 0) or 0)
        bear = (recs.get("strong_sell", 0) or 0) * 2 + (recs.get("sell", 0) or 0)
        if bull > bear + 5:
            score += 15
            reasons.append(f"📈 Analyst bullish")
            if direction == "NEUTRAL":
                direction = "BULLISH"
        elif bear > bull + 5:
            score += 15
            reasons.append(f"📉 Analyst bearish")
            if direction == "NEUTRAL":
                direction = "BEARISH"

    # 5. Earnings
    earnings = data.get("upcoming_earnings")
    if earnings:
        try:
            days = (datetime.strptime(earnings["date"], "%Y-%m-%d").date() - datetime.utcnow().date()).days
        except (KeyError, TypeError, ValueError):
            days = -1
        if 0 <= days < 7:
            score += 35
            reasons.append(f"🚨 Earnings in {days} days!")
        elif 7 <= days < 14:
            score += 20
            reasons.append(f"📅 Earnings in {days} days")

    # 6. Sentiment
    sentiment = (data.get("sentiment") or {})
    news_score = sentiment.get("company_news_score", 0)
    if news_score > 0.6:
        score += 15
        reasons.append("😊 Very positive sentiment")
        if direction == "NEUTRAL":
            direction = "BULLISH"
    elif news_score > 0.3:
        score += 8
        reasons.append("🙂 Positive sentiment")
    elif news_score < -0.4:
        score += 15
        reasons.append("😟 Very negative sentiment")
        if direction == "NEUTRAL":
            direction = "BEARISH"
    elif news_score < -0.2:
        score += 8
        reasons.append("😕 Negative sentiment")

    # 7. Option cost
    opt_cost = estimate_option_cost(data.get("quote", {}).get("current_price", 0))
    if opt_cost.get("tier") == "budget":
        score += 10
        reasons.append("💚 Very low option cost")

    return {"score": score, "reasons": reasons, "direction": direction}


async def scan_watchlist(category: str, user_role: str = "free") -> dict:
    """Scan a watchlist category"""
    watchlist = WATCHLISTS.get(category)
    if not watchlist:
        raise Exception(f"Unknown category: {category}")

    if watchlist["tier"] == "pro" and user_role != "pro":
        raise Exception("PRO_REQUIRED")

    results = []
    tickers = watchlist["tickers"]

    # Fetch data for each ticker
    for ticker in tickers:
        try:
            data = await finnhub_client.fetch_all_data(ticker)
            scored = score_stock(data)
            option_cost = estimate_option_cost(data.get("quote", {}).get("current_price", 0))

            profile = data.get("profile") or {}
            quote = data.get("quote") or {}
            news = data.get("news", [])

            result = {
                "ticker": ticker,
                "name": profile.get("name", ticker),
                "logo": profile.get("logo"),
                "current_price": quote.get("current_price", 0),
                "change_pct": quote.get("change_pct", 0),
                "market_cap": profile.get("market_cap"),
                "score": scored["score"],
                "reasons": scored["reasons"],
                "direction": scored["direction"],
                "option_cost": option_cost,
                "news_count": len(news),
                "top_news": {
                    "title": news[0]["title"],
                    "published_label": news[0]["published_label"],
                    "publisher": news[0]["publisher"],
                } if news else None,
                "upcoming_earnings": data.get("upcoming_earnings"),
            }
            results.append(result)
        except Exception as e:
            print(f"Scan error {ticker}: {str(e)}")
            continue

    results.sort(key=lambda x: x["score"], reverse=True)

    from datetime import datetime
    return {
        "category": category,
        "category_label": watchlist["label"],
        "category_desc": watchlist.get("description", ""),
        "scanned_at": datetime.utcnow().isoformat(),
        "total_scanned": len(tickers),
        "results": results,
    }
