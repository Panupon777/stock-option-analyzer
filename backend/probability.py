import math


def erf(x):
    """Error function approximation"""
    a = [0.254829592, -0.284496736, 1.421413741, -1.453152027, 1.061405429]
    p = 0.3275911
    sign = 1 if x >= 0 else -1
    x = abs(x)
    t = 1.0 / (1.0 + p * x)
    y = 1.0 - (((((a[4] * t + a[3]) * t) + a[2]) * t + a[1]) * t + a[0]) * t * math.exp(-x * x)
    return sign * y


def normal_cdf(x):
    """Normal cumulative distribution function"""
    return 0.5 * (1 + erf(x / math.sqrt(2)))


def calc_probability(
    current_price: float,
    target_price: float,
    days_left: int,
    iv: float = 0.5,
    risk_free_rate: float = 0.05,
) -> dict:
    """Calculate probability using Black-Scholes model"""
    T = days_left / 365.0
    S = current_price
    K = target_price
    r = risk_free_rate
    sigma = iv

    if T <= 0 or S <= 0 or K <= 0 or sigma <= 0:
        return {"probability": 0, "direction": "N/A", "pct_move": 0}

    d2 = (math.log(S / K) + (r - 0.5 * sigma * sigma) * T) / (sigma * math.sqrt(T))

    prob_call = normal_cdf(d2) * 100
    prob_put = normal_cdf(-d2) * 100

    pct_move = ((K - S) / S) * 100
    direction = "UP" if K >= S else "DOWN"

    return {
        "probability": round(prob_call * 10) / 10 if direction == "UP" else round(prob_put * 10) / 10,
        "prob_call": round(prob_call * 10) / 10,
        "prob_put": round(prob_put * 10) / 10,
        "direction": direction,
        "pct_move": round(pct_move * 100) / 100,
        "days_left": days_left,
        "iv": round(iv * 100),
    }


def generate_option_levels(
    current_price: float,
    iv: float = 0.5,
    days_left: int = 13,
    direction: str = "UP",
) -> list:
    """Generate option levels (เบาเบา/พอไหว/สุดใจ) like broker style"""
    S = current_price
    T = days_left / 365.0
    sigma = iv

    move_1 = S * sigma * math.sqrt(T)

    if direction == "UP":
        levels = [
            {"label": "เบาเบา", "emoji": "🟢", "multiplier": 0.4, "payout": 50},
            {"label": "พอไหว", "emoji": "🟡", "multiplier": 1.0, "payout": 100},
            {"label": "สุดใจ", "emoji": "🔴", "multiplier": 1.6, "payout": 200},
        ]
    else:
        levels = [
            {"label": "เบาเบา", "emoji": "🟢", "multiplier": -0.4, "payout": 50},
            {"label": "พอไหว", "emoji": "🟡", "multiplier": -1.0, "payout": 100},
            {"label": "สุดใจ", "emoji": "🔴", "multiplier": -1.6, "payout": 200},
        ]

    result = []
    for lv in levels:
        target = round((S + lv["multiplier"] * move_1) * 100) / 100
        prob = calc_probability(S, target, days_left, sigma)
        expected_value = round((prob["probability"] / 100 * lv["payout"] - (1 - prob["probability"] / 100) * 100) * 10) / 10

        recommendation = "ดี" if prob["probability"] > 55 else "ปานกลาง" if prob["probability"] > 40 else "เสี่ยงสูง"

        result.append({
            "label": lv["label"],
            "emoji": lv["emoji"],
            "target_price": target,
            "pct_move": prob["pct_move"],
            "probability": prob["probability"],
            "payout": lv["payout"],
            "expected_value": expected_value,
            "recommendation": recommendation,
        })

    return result
