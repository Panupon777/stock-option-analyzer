from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime


# ─────────────────────
# Auth Schemas
# ─────────────────────
class UserRegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)
    name: str


class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: int
    email: str
    name: str
    role: str


class AuthResponse(BaseModel):
    token: str
    user: UserResponse


class MeResponse(BaseModel):
    user: UserResponse
    usage_today: int


# ─────────────────────
# Subscription Schemas
# ─────────────────────
class SubscriptionRequest(BaseModel):
    slip_note: Optional[str] = ""


class SubscriptionResponse(BaseModel):
    success: bool
    promptpay: str
    amount: int
    original_price: Optional[int] = None
    is_flash_sale: bool = False
    sale_label: Optional[str] = None
    message: str


class SubscriptionStatus(BaseModel):
    subscription: Optional[dict] = None
    role: str
    promptpay: str
    amount: int


class SubscriptionItem(BaseModel):
    id: int
    user_id: int
    email: str
    name: str
    amount: int
    slip_note: str
    status: str
    created_at: datetime


# ─────────────────────
# Stock Analysis Schemas
# ─────────────────────
class AnalyzeRequest(BaseModel):
    ticker: str
    market: str = "US"
    horizon: str = "weekly"


class OptionLevel(BaseModel):
    label: str
    emoji: str
    target_price: float
    pct_move: float
    probability: float
    payout: int
    expected_value: float
    recommendation: str


class AnalysisResponse(BaseModel):
    ticker: str
    direction: str
    confidence: int
    summary_th: str
    current_price: float
    price_target: float
    option_strategy: dict
    call_explanation: str
    put_explanation: str
    option_levels: List[OptionLevel]
    sentiment_scores: dict
    factors: List[dict]
    key_news: List[dict]
    price_scenarios: dict
    stock_data: dict
    model_used: str


# ─────────────────────
# Scanner Schemas
# ─────────────────────
class ScannerCategory(BaseModel):
    key: str
    label: str
    count: int
    tier: str
    description: Optional[str] = None
    locked: bool = False


class ScanResult(BaseModel):
    ticker: str
    name: str
    logo: Optional[str] = None
    current_price: float
    change_pct: float
    market_cap: Optional[int] = None
    score: int
    reasons: List[str]
    direction: str
    option_cost: dict
    news_count: int
    top_news: Optional[dict] = None
    upcoming_earnings: Optional[dict] = None


class ScannerResults(BaseModel):
    category: str
    category_label: str
    category_desc: str
    scanned_at: datetime
    total_scanned: int
    results: List[ScanResult]


# ─────────────────────
# Flash Sale Schemas
# ─────────────────────
class FlashSaleResponse(BaseModel):
    original_price: int
    sale_price: int
    discount_pct: int
    label: str
    ends_at: datetime
    started_at: datetime


class FlashSaleCreateRequest(BaseModel):
    price: int
    discount_pct: int
    label: str
    duration_minutes: int


# ─────────────────────
# Admin Schemas
# ─────────────────────
class ApproveSubscriptionResponse(BaseModel):
    success: bool
    message: str


class FlashSaleSetResponse(BaseModel):
    success: bool
    sale: FlashSaleResponse


# ─────────────────────
# Health Check
# ─────────────────────
class HealthResponse(BaseModel):
    status: str
    anthropic: bool
    finnhub: bool
