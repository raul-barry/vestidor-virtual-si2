from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import model_validator


class Settings(BaseSettings):
    project_name: str = "Vestidor Virtual API"
    environment: str = "development"
    database_url: str
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    password_reset_token_expire_minutes: int = 30
    expose_reset_token: bool = False
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    smtp_starttls: bool = True
    smtp_ssl: bool = False
    cors_origins: str = "http://localhost:4200,http://127.0.0.1:4200,http://localhost:4300,http://127.0.0.1:4300"
    stripe_secret_key: str = ""
    stripe_publishable_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_currency: str = "BOB"
    # Demo mode never sends card data to Stripe. It is useful for presentations
    # and local development, where each selected payment method can be accepted.
    payment_simulation_mode: bool = True
    fashn_api_key: str = ""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @model_validator(mode="before")
    @classmethod
    def default_production_payment_mode(cls, values):
        # Local development keeps demo payments enabled, while an omitted
        # setting in production must never enable simulated charges.
        if isinstance(values, dict) and values.get("environment") == "production" and "payment_simulation_mode" not in values:
            values["payment_simulation_mode"] = False
        return values

    @model_validator(mode="after")
    def validate_production(self):
        if self.environment == "production":
            if len(self.secret_key) < 32 or self.secret_key.startswith(("change-me", "REPLACE_")):
                raise ValueError("Production requires a random SECRET_KEY of at least 32 characters")
            if self.expose_reset_token:
                raise ValueError("EXPOSE_RESET_TOKEN must be false in production")
            if not self.cors_origins.strip() or "*" in self.cors_origins:
                raise ValueError("Production requires explicit CORS origins")
            if self.payment_simulation_mode:
                raise ValueError("PAYMENT_SIMULATION_MODE must be false in production")
        return self

    @property
    def smtp_configured(self) -> bool:
        """SMTP is usable when a host and sender address are configured."""
        return bool(self.smtp_host.strip() and self.smtp_from.strip())


settings = Settings()
