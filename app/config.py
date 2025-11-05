from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):

    MONGODB_URL: str = "mongodb://localhost:27017"
    MONGODB_DB_NAME: str = "documind_ai"

    GROQ_API_KEY: str
    GROQ_MODEL: str = "llama-3.3-70b-versatile"

    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 10080

    CHROMA_PERSIST_DIR: str = "./chroma_db"

    EMBEDDING_MODEL: str = "multi-qa-mpnet-base-dot-v1"
    EMBEDDING_DEVICE: str = "cpu"

    HOST: str = "0.0.0.0"
    PORT: int = 8000
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:5173"

    UPLOAD_DIR: str = "./uploads"
    MAX_FILE_SIZE: int = 52428800

    RATE_LIMIT_PER_MINUTE: int = 10
    RATE_LIMIT_PER_HOUR: int = 100

    MIN_CHUNK_SIZE: int = 300
    MAX_CHUNK_SIZE: int = 1200
    CHUNK_OVERLAP: int = 100

    TOP_K_CHUNKS: int = 5
    RERANK_TOP_K: int = 3

    @property
    def origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True
    )


settings = Settings()
