from typing import List, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "backend/.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database (PostgreSQL with psycopg v3 sync driver)
    DATABASE_URL: str = "postgresql+psycopg://postgres:postgres@localhost:5432/examination_osm"

    # Application
    PROJECT_NAME: str = "Digital Examination & OSM Platform"
    API_V1_STR: str = "/api/v1"
    DEBUG: bool = False

    # Security / JWT
    JWT_SECRET: str = "dev_secret_key_please_change_in_production"
    JWT_EXPIRE_MINUTES: int = 480

    # CORS
    CORS_ORIGINS: Union[str, List[str]] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, list):
            return v
        return ["http://localhost:5173", "http://127.0.0.1:5173"]

    # Storage
    STORAGE_BACKEND: str = "local"
    LOCAL_STORAGE_DIR: str = "./storage"
    S3_BUCKET: str = ""
    S3_ENDPOINT: str = ""
    S3_KEY: str = ""
    S3_SECRET: str = ""

    # Limits & Workers
    MAX_UPLOAD_MB: int = 15
    JOB_WORKERS: int = 4

    # AI / OCR / Embedding / Vector DB settings (loaded from env)
    OCR_PROVIDER: str = "vision"
    GOOGLE_APPLICATION_CREDENTIALS: str = ""
    LLM_PROVIDER: str = "anthropic"
    LLM_MODEL: str = "claude-3-5-sonnet-20241022"
    ANTHROPIC_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    EMBEDDING_PROVIDER: str = ""
    EMBEDDING_MODEL: str = ""
    EMBEDDING_DIM: int = 1536
    OPENAI_API_KEY: str = ""
    PINECONE_API_KEY: str = ""
    PINECONE_INDEX: str = "exam-references"


settings = Settings()
