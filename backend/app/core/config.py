from pydantic_settings import BaseSettings, SettingsConfigDict


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

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
