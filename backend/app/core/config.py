import os
import json
from typing import List, Union, Optional
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "AI-HMS"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"  # development, staging, production
    
    DEFAULT_DEV_SECRET_KEY: str = "ai_hms_super_secret_jwt_key_development_2026_change_in_production"
    SECRET_KEY: str = "ai_hms_super_secret_jwt_key_development_2026_change_in_production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    
    # LLM & Grounded Clinical AI Configuration
    LLM_PROVIDER: str = "ollama"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    GEMINI_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None
    LLM_MODEL_NAME: str = "Qwen3-4B:latest"
    
    # ML Risk Categorization Thresholds (Configurable per hospital clinic policy)
    ML_NO_SHOW_HIGH_THRESHOLD: float = 0.245
    ML_NO_SHOW_MEDIUM_THRESHOLD: float = 0.220
    
    # PostgreSQL Database Configuration
    DB_HOST: str = "127.0.0.1"
    DB_PORT: int = 5432
    DB_NAME: str = "ai_hms"
    DB_USER: str = "postgres"
    DB_PASSWORD: str = ""
    DATABASE_URL: str = ""

    # Connection Pooling for High Concurrency
    DB_POOL_SIZE: int = 15
    DB_MAX_OVERFLOW: int = 25
    DB_POOL_RECYCLE: int = 1800  # 30 minutes
    DB_POOL_TIMEOUT: int = 30
    
    @property
    def sync_database_url(self) -> str:
        if self.DATABASE_URL:
            # Normalize url for psycopg2
            url = self.DATABASE_URL
            if url.startswith("postgresql://") and not url.startswith("postgresql+psycopg2://"):
                url = url.replace("postgresql://", "postgresql+psycopg2://", 1)
            return url
        pwd = f":{self.DB_PASSWORD}" if self.DB_PASSWORD else ""
        return f"postgresql+psycopg2://{self.DB_USER}{pwd}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    CORS_ORIGINS: Union[List[str], str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            if v.startswith("["):
                try:
                    return json.loads(v)
                except Exception:
                    pass
            return [i.strip() for i in v.split(",") if i.strip()]
        return v

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() in ("production", "prod")

    def validate_production_security(self) -> None:
        """
        Validates security requirements for production environments.
        Fails fast if insecure default keys or configurations are detected.
        """
        if self.is_production:
            if self.SECRET_KEY == self.DEFAULT_DEV_SECRET_KEY:
                raise ValueError(
                    "FATAL SECURITY CONFIGURATION ERROR: "
                    "The default development SECRET_KEY is being used in a production environment! "
                    "Please generate and set a strong, unique SECRET_KEY in your .env or environment variables."
                )

    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
