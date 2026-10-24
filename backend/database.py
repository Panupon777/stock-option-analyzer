from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, JSON, ForeignKey, Text, Enum as SQLEnum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import enum
from config import settings

DATABASE_URL = settings.database_url

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class UserRole(str, enum.Enum):
    free = "free"
    pro = "pro"


class SubscriptionStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    name = Column(String, nullable=False)
    role = Column(SQLEnum(UserRole), default=UserRole.free)
    created_at = Column(DateTime, default=datetime.utcnow)


class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    status = Column(SQLEnum(SubscriptionStatus), default=SubscriptionStatus.pending)
    plan = Column(String, default="pro")
    amount = Column(Integer, nullable=False)
    slip_note = Column(String, default="")
    approved_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class AnalysisHistory(Base):
    __tablename__ = "analysis_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    ticker = Column(String, nullable=False)
    market = Column(String, default="US")
    direction = Column(String)
    confidence = Column(Integer)
    result = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)


class DailyUsage(Base):
    __tablename__ = "daily_usage"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    date = Column(String, nullable=False)  # YYYY-MM-DD format
    count = Column(Integer, default=0)

    __table_args__ = ({"__table_args__": "UNIQUE(user_id, date)"},)


class FlashSale(Base):
    __tablename__ = "flash_sales"

    id = Column(Integer, primary_key=True, index=True)
    original_price = Column(Integer, nullable=False)
    sale_price = Column(Integer, nullable=False)
    discount_pct = Column(Integer, nullable=False)
    label = Column(String, nullable=False)
    started_at = Column(DateTime, default=datetime.utcnow)
    ends_at = Column(DateTime, nullable=False)
    is_active = Column(Boolean, default=True)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    """Create all tables"""
    Base.metadata.create_all(bind=engine)
