import httpx
from datetime import datetime, timedelta
from typing import Optional
from config import settings


BASE_URL = "https://finnhub.io/api/v1"


async def call_finnhub(endpoint: str, params: dict = None) -> dict:
    if not settings.finnhub_api_key:
        raise Exception("FINNHUB_API_KEY not set")
    
    if params is None:
        params = {}
    params["token"] = settings.finnhub_api_key
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{BASE_URL}{endpoint}", params=params, timeout=15.0)
            if response.status_code != 200:
                raise Exception(f"Finnhub {response.status_code}")
            return response.json()
        except httpx.TimeoutException:
            raise Exception("Finnhub timeout")
        except Exception as e:
            raise e


def format_time_ago(dt: datetime) -> str:
    if not dt:
        return "Unknown"
    diff = datetime.utcnow() - dt
    mins = int(diff.total_seconds() / 60)
    hours = mins // 60
    days = hours // 24

    if mins < 2:
        return "Just fetched"
    elif mins < 60:
        return f"{mins} minutes ago"
    elif hours < 24:
        return f"{hours} hours ago"
    else:
        return f"{days} days ago"


async def get_quote(ticker: str) -> dict:
    return await call_finnhub("/quote", {"symbol": ticker.upper()})


async def get_profile(ticker: str) -> dict:
    return await call_finnhub("/stock/profile2", {"symbol": ticker.upper()})


async def get_company_news(ticker: str, days_back: int = 14) -> list:
    to = datetime.utcnow()
    from_date = to - timedelta(days=days_back)
    from_str = from_date.strftime("%Y-%m-%d")
    to_str = to.strftime("%Y-%m-%d")
    return await call_finnhub("/company-news", {"symbol": ticker.upper(), "from": from_str, "to": to_str})


async def get_recommendations(ticker: str) -> dict:
    results = await call_finnhub("/stock/recommendation", {"symbol": ticker.upper()})
    return results[0] if isinstance(results, list) and results else {}


async def get_news_sentiment(ticker: str) -> Optional[dict]:
    try:
        return await call_finnhub("/news-sentiment", {"symbol": ticker.upper()})
    except:
        return None


async def get_earnings(ticker: str) -> Optional[dict]:
    try:
        data = await call_finnhub("/calendar/earnings", {"symbol": ticker.upper()})
        earnings_list = data.get("earningsCalendar", [])
        return earnings_list[0] if earnings_list else None
    except:
        return None


async def fetch_all_data(ticker: str) -> dict:
    """Fetch all Finnhub data for analysis"""
    fetched_at = datetime.utcnow()
    T = ticker.upper()

    try:
        quote_data = await get_quote(T)
    except Exception as e:
        raise Exception(f"No stock data found for {T} — please check the ticker")

    if not quote_data or not quote_data.get("c"):
        raise Exception(f"No stock data found for {T}")

    profile_data = await get_profile(T) if quote_data else None
    news_data = await get_company_news(T, 14) if quote_data else []
    recs_data = await get_recommendations(T) if quote_data else {}
    sentiment_data = await get_news_sentiment(T)
    earnings_data = await get_earnings(T)

    # Parse quote
    q = quote_data or {}
    quote_ts = datetime.fromtimestamp(q.get("t", 0)) if q.get("t") else datetime.utcnow()

    return {
        "fetched_at": fetched_at.isoformat(),
        "fetched_at_label": format_time_ago(fetched_at),
        "profile": {
            "name": profile_data.get("name") if profile_data else None,
            "exchange": profile_data.get("exchange") if profile_data else None,
            "industry": profile_data.get("finnhubIndustry") if profile_data else None,
            "market_cap": profile_data.get("marketCapitalization") if profile_data else None,
            "shares": profile_data.get("shareOutstanding") if profile_data else None,
            "ipo": profile_data.get("ipo") if profile_data else None,
            "logo": profile_data.get("logo") if profile_data else None,
            "country": profile_data.get("country") if profile_data else None,
            "currency": profile_data.get("currency") if profile_data else None,
        } if profile_data else None,
        "quote": {
            "current_price": q.get("c", 0),
            "change": q.get("d", 0),
            "change_pct": q.get("dp", 0),
            "day_high": q.get("h", 0),
            "day_low": q.get("l", 0),
            "open": q.get("o", 0),
            "previous_close": q.get("pc", 0),
            "timestamp": quote_ts.isoformat(),
            "timestamp_label": format_time_ago(quote_ts),
        },
        "news": [
            {
                "title": n.get("headline", ""),
                "summary": n.get("summary", ""),
                "publisher": n.get("source", ""),
                "url": n.get("url", ""),
                "category": n.get("category", ""),
                "published_at": datetime.fromtimestamp(n.get("datetime", 0)).isoformat() if n.get("datetime") else None,
                "published_label": format_time_ago(datetime.fromtimestamp(n.get("datetime", 0))) if n.get("datetime") else "N/A",
                "is_stale": (datetime.utcnow() - datetime.fromtimestamp(n.get("datetime", 0))).days > 7 if n.get("datetime") else False,
            }
            for n in (news_data or [])[:10]
        ],
        "recommendations": {
            "period": recs_data.get("period") if recs_data else None,
            "strong_buy": recs_data.get("strongBuy", 0) if recs_data else 0,
            "buy": recs_data.get("buy", 0) if recs_data else 0,
            "hold": recs_data.get("hold", 0) if recs_data else 0,
            "sell": recs_data.get("sell", 0) if recs_data else 0,
            "strong_sell": recs_data.get("strongSell", 0) if recs_data else 0,
        } if recs_data else None,
        "sentiment": {
            "buzz": sentiment_data.get("buzz") if sentiment_data else None,
            "sentiment": sentiment_data.get("sentiment") if sentiment_data else None,
            "company_news_score": sentiment_data.get("companyNewsScore") if sentiment_data else None,
        } if sentiment_data else None,
        "upcoming_earnings": {
            "date": earnings_data.get("date") if earnings_data else None,
            "hour": earnings_data.get("hour") if earnings_data else None,
            "eps_estimate": earnings_data.get("epsEstimate") if earnings_data else None,
        } if earnings_data else None,
    }
