from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    database_url: str
    anthropic_api_key: str = ""
    finnhub_api_key: str = ""
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 720
    admin_password: str
    promptpay_number: str = ""
    subscription_price: int = 299
    port: int = 8000
    debug: bool = False

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
