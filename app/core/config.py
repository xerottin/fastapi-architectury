from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):

    # Application
    app_name: str = "Fast-Arch Backend"
    app_version: str = "1.0.0"
    root_path: str = ""
    rate_limit_max_requests: int = 1000
    rate_limit_window_seconds: int = 600
    gzip_minimum_size: int = 500
    cors_max_age: int = 3600
    cors_origins: List[str] = ["http://localhost:3000"]
    allowed_hosts: List[str] = ["*"]

    sentry_dsn: str | None = None
    debug: bool = True
    environment: str = "local"

    # JWT
    jwt_secret_key: str = "your-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 10080
    jwt_refresh_token_expire_hours: int = 168

    # Database
    db_host: str = "localhost"
    db_port: int = 5432
    db_user: str = "postgres"
    db_pass: str = "postgres"
    db_name: str = "fast_arch_backend_db"

    @property
    def database_url_asyncpg(self) -> str:
        return f"postgresql+asyncpg://{self.db_user}:{self.db_pass}@{self.db_host}:{self.db_port}/{self.db_name}"

    @property
    def database_url_psycopg(self) -> str:
        return f"postgresql+psycopg2://{self.db_user}:{self.db_pass}@{self.db_host}:{self.db_port}/{self.db_name}"

    # OpenAI
    openai_api_key: str = ""

    # MinIO
    minio_endpoint: str = "localhost:9211"
    minio_public_url: str = "http://localhost:9211"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_secure: bool = False
    aws_storage_region: str = "us-east-1"
    minio_bucket: str = "minio_bucket"

    # Redis
    redis_url: str = "redis://localhost:6379"

    # MongoDB
    mongo_uri: str = "mongodb://root:example@mongo:27017/admin"
    mongo_db_name: str = "fast_architectury"

    # Celery
    rabbitmq_url: str = "amqp://guest:guest@rabbitmq:5672//"
    # Sentry (Celery)
    sentry_dsn_celery: str = ""
    sentry_traces_sample_rate: str = ""
    sentry_profiles_sample_rate: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
        env_file_encoding="utf-8",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
