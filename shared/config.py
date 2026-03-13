"""鍏ㄥ眬閰嶇疆"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    """搴旂敤閰嶇疆"""
    
    # 搴旂敤淇℃伅
    app_name: str = "Digital Goods Platform"
    app_version: str = "0.1.0"
    debug: bool = True
    
    # 鏁版嵁搴撻厤缃?
    database_url: str = "postgresql+asyncpg://postgres:postgres@127.0.0.1:5432/reflex"
    database_echo: bool = False
    
    # Redis 閰嶇疆
    redis_url: str = "redis://localhost:6379/0"
    export_task_backend: str = "db"
    push_queue_backend: str = "db"
    
    # Telegram Bot 閰嶇疆
    bot_token: Optional[str] = None
    
    # USDT 鏀粯閰嶇疆
    trongrid_api_key: Optional[str] = None
    usdt_contract_address: str = "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"  # TRC20 USDT
    
    # 瀹夊叏閰嶇疆
    secret_key: str = "your-secret-key-change-in-production"
    access_token_expire_minutes: int = 60 * 24  # 24 hours
    
    # 鍒嗛〉閰嶇疆
    default_page_size: int = 20
    max_page_size: int = 100
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache()
def get_settings() -> Settings:
    """鑾峰彇閰嶇疆鍗曚緥"""
    return Settings()


settings = get_settings()
