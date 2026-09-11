from functools import lru_cache

from pydantic import Field, MySQLDsn, RedisDsn, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore")
    app_name: str = "DukaMe API"
    app_version: str = "0.2.0"
    environment: str = "development"
    debug: bool = False
    log_level: str = "INFO"
    database_url: MySQLDsn = Field(alias="DATABASE_URL")
    redis_url: RedisDsn = Field(alias="REDIS_URL")
    jwt_secret: SecretStr = Field(alias="JWT_SECRET")
    jwt_algorithm: str = "HS256"
    database_pool_size: int = Field(default=10, ge=1, le=100)
    database_max_overflow: int = Field(default=20, ge=0, le=200)
    database_pool_recycle: int = Field(default=1800, ge=60)
    database_pool_timeout: float = Field(default=10.0, gt=0)
    rate_limit_enabled: bool = True
    rate_limit_requests: int = Field(default=120, ge=1)
    rate_limit_window_seconds: int = Field(default=60, ge=1)
    access_token_ttl_seconds: int = Field(default=900, ge=60, le=3600)
    refresh_token_ttl_seconds: int = Field(default=2592000, ge=3600, le=31536000)
    refresh_token_bytes: int = Field(default=32, ge=32, le=128)
    default_plan_slug: str = "free"
    media_root: str = "uploads"
    media_max_bytes: int = Field(default=5 * 1024 * 1024, ge=1024, le=25 * 1024 * 1024)
    cart_session_ttl_seconds: int = Field(default=2592000, ge=3600, le=31536000)
    cart_item_max_quantity: int = Field(default=1000, ge=1, le=100000)
    trusted_hosts: list[str] = Field(default_factory=lambda: ["localhost", "127.0.0.1", "dukamedev.local"])
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173", "http://127.0.0.1:5173", "http://dukamedev.local:5173"])
    frontend_base_url: str = "http://dukamedev.local:5173"
    sms_provider: str = "none"
    sms_api_key: SecretStr | None = None
    sms_username: str | None = None
    sms_sender_id: str | None = None
    sms_api_url: str = "https://api.africastalking.com/version1/messaging"
    notification_poll_seconds: float = Field(default=2.0, ge=1.0, le=60.0)
    notification_max_attempts: int = Field(default=5, ge=1, le=20)

    @field_validator("environment")
    @classmethod
    def validate_environment(cls, value: str) -> str:
        allowed = {"development", "staging", "production", "test"}
        if value not in allowed:
            raise ValueError(f"environment must be one of {sorted(allowed)}")
        return value

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
