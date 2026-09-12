from functools import lru_cache
import secrets

from pydantic import Field, MySQLDsn, RedisDsn, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )
    app_name: str = "DukaMe API"
    app_version: str = "0.2.0"
    environment: str = "development"
    debug: bool = False
    log_level: str = "INFO"
    database_url: MySQLDsn = Field(alias="DATABASE_URL")
    redis_url: RedisDsn = Field(alias="REDIS_URL")
    jwt_secret: SecretStr = Field(alias="JWT_SECRET")
    tracking_secret: SecretStr | None = None
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
    default_billing_currency: str = Field(default="KES", min_length=3, max_length=3)
    billing_intervals: list[str] = Field(
        default_factory=lambda: ["monthly", "quarterly", "yearly"]
    )
    billing_interval_days_monthly: int = Field(default=30, ge=1, le=366)
    billing_interval_days_quarterly: int = Field(default=90, ge=1, le=400)
    billing_interval_days_yearly: int = Field(default=365, ge=1, le=400)
    subscription_invoice_due_days: int = Field(default=3, ge=0, le=30)
    subscription_renewal_lead_days: int = Field(default=3, ge=0, le=30)
    # Platform (DukaMe SaaS) M-Pesa — used for subscription billing, not store orders.
    platform_mpesa_enabled: bool = False
    platform_mpesa_consumer_key: str | None = None
    platform_mpesa_consumer_secret: SecretStr | None = None
    platform_mpesa_shortcode: str | None = None
    platform_mpesa_passkey: SecretStr | None = None
    platform_mpesa_environment: str = "sandbox"
    platform_mpesa_transaction_type: str = "CustomerPayBillOnline"
    platform_mpesa_account_reference: str = "DukaMe"
    platform_mpesa_transaction_desc: str = "Subscription"
    media_root: str = "uploads"
    media_max_bytes: int = Field(default=5 * 1024 * 1024, ge=1024, le=25 * 1024 * 1024)
    cart_session_ttl_seconds: int = Field(default=2592000, ge=3600, le=31536000)
    cart_item_max_quantity: int = Field(default=1000, ge=1, le=100000)
    delivery_otp_ttl_minutes: int = Field(default=15, ge=1, le=120)
    delivery_otp_max_attempts: int = Field(default=5, ge=1, le=20)
    trusted_hosts: list[str] = Field(
        default_factory=lambda: ["localhost", "127.0.0.1", "dukamedev.local"]
    )
    # Extra browser origins may be supplied with CORS_ORIGINS. The primary frontend
    # origin always comes from FRONTEND_BASE_URL, so its port is configured once.
    cors_origins: list[str] = Field(default_factory=list)
    frontend_base_url: str = "http://dukamedev.local:4173"
    public_api_base_url: str = "http://dukamedev.local:8000"
    payment_encryption_key: SecretStr | None = None
    sms_provider: str = "none"
    sms_api_key: SecretStr | None = None
    sms_username: str | None = None
    sms_sender_id: str | None = None
    sms_api_url: str = "https://api.africastalking.com/version1/messaging"
    whatsapp_provider: str = "none"
    whatsapp_api_token: SecretStr | None = None
    whatsapp_phone_number_id: str | None = None
    whatsapp_api_base_url: str = "https://graph.facebook.com/v21.0"
    whatsapp_api_url: str = ""
    whatsapp_status_template: str = "order_status_update"
    whatsapp_template_language: str = "en"
    whatsapp_require_opt_in: bool = True
    notification_poll_seconds: float = Field(default=2.0, ge=1.0, le=60.0)
    notification_max_attempts: int = Field(default=5, ge=1, le=20)
    notification_lease_seconds: int = Field(default=60, ge=30, le=600)
    notification_max_backoff_seconds: int = Field(default=300, ge=5, le=86400)
    notification_worker_id: str = Field(
        default_factory=lambda: secrets.token_hex(16), min_length=1, max_length=64
    )
    maintenance_interval_seconds: int = Field(default=300, ge=30, le=86400)

    @field_validator("environment")
    @classmethod
    def validate_environment(cls, value: str) -> str:
        allowed = {"development", "staging", "production", "test"}
        if value not in allowed:
            raise ValueError(f"environment must be one of {sorted(allowed)}")
        return value

    @field_validator("default_billing_currency")
    @classmethod
    def validate_currency(cls, value: str) -> str:
        return value.upper()

    @model_validator(mode="after")
    def include_primary_frontend_origin(self) -> "Settings":
        origin = self.frontend_base_url.rstrip("/")
        if origin not in self.cors_origins:
            self.cors_origins.append(origin)
        return self

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def tracking_signing_key(self) -> str:
        return (self.tracking_secret or self.jwt_secret).get_secret_value()


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
