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
    cors_origins: str = "http://localhost:4200,http://127.0.0.1:4200,http://localhost:4300,http://127.0.0.1:4300"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @model_validator(mode="after")
    def validate_production(self):
        if self.environment == "production":
            if len(self.secret_key) < 32 or self.secret_key.startswith(("change-me", "REPLACE_")):
                raise ValueError("Production requires a random SECRET_KEY of at least 32 characters")
            if self.expose_reset_token:
                raise ValueError("EXPOSE_RESET_TOKEN must be false in production")
            if not self.cors_origins.strip() or "*" in self.cors_origins:
                raise ValueError("Production requires explicit CORS origins")
        return self


settings = Settings()
