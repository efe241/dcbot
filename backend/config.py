import os
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict
from decimal import Decimal

class Settings(BaseSettings):
    # App
    ENVIRONMENT: str = "development"
    SECRET_KEY: str = "super-secret-key-change-in-production-1234567890"
    BASE_URL: str = "http://localhost:8000"
    PORT: int = 8000

    # Discord
    DISCORD_BOT_TOKEN: str = "mock_bot_token"
    DISCORD_CLIENT_ID: str = "123456789"
    DISCORD_CLIENT_SECRET: str = "mock_client_secret"
    DISCORD_REDIRECT_URI: str = "http://localhost:8000/api/auth/callback"
    ADMIN_DISCORD_IDS: str = ""
    ADMIN_PASSWORD: str = "Me261211@"

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:////tmp/cpx_coins.db" if os.environ.get("VERCEL") else "sqlite+aiosqlite:///./cpx_coins.db"

    # CPX Settings
    CPX_APP_ID: str = "35266"
    CPX_APP_SECURE_HASH: str = "sample_secure_hash_secret"
    CPX_IP_WHITELIST: str = "188.40.3.73,157.90.97.92,2a01:4f8:d0a:30ff::,127.0.0.1,testclient"

    # AdGem Settings
    ADGEM_APP_ID: str = "33188"
    ADGEM_SECRET_KEY: str = "3hJsDUnwJMpxDDoTGyqUma0w"
    ADGEM_IP_WHITELIST: str = "52.42.57.127,54.186.196.74,54.218.125.178,127.0.0.1,testclient,*"

    # Economy
    COINS_PER_USD: Decimal = Decimal("100")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @property
    def allowed_cpx_ips(self) -> List[str]:
        return [ip.strip() for ip in self.CPX_IP_WHITELIST.split(",") if ip.strip()]

    @property
    def allowed_adgem_ips(self) -> List[str]:
        return [ip.strip() for ip in self.ADGEM_IP_WHITELIST.split(",") if ip.strip()]

    @property
    def admin_ids_list(self) -> List[str]:
        return [uid.strip() for uid in self.ADMIN_DISCORD_IDS.split(",") if uid.strip()]

settings = Settings()
