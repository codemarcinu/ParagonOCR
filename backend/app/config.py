"""
Configuration settings for ParagonOCR Web Edition.

Loads environment variables from .env file and provides typed configuration.
"""

import os
from typing import List, Union, Any
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # API Configuration
    API_V1_PREFIX: str = "/api/v1"
    CORS_ORIGINS: Any = Field(
        # Vite dev server ports and common development ports
        default=[
            "http://localhost:3000",
            "http://localhost:5173", 
            "http://localhost:5174", 
            "http://localhost:5175",
            "http://localhost:5176",
            "http://localhost:5177",
            "http://localhost:5179",  # Current Vite port
        ],
        description="Allowed CORS origins",
    )

    # Security Configuration
    SECRET_KEY: str = Field(
        default="09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7",
        description="Secret key for JWT",
    )
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=30, description="Access token expiration time in minutes"
    )

    # Database Configuration
    DATABASE_URL: str = Field(
        default="sqlite:///./data/receipts.db", description="SQLite database URL"
    )
    DATABASE_ECHO: bool = Field(
        default=False, description="Echo SQL queries (for debugging)"
    )

    # OCR Configuration
    OCR_ENGINE: str = Field(
        default="tesseract", description="OCR engine: 'tesseract' or 'easyocr'"
    )
    USE_GPU_OCR: bool = Field(
        default=False, description="Use GPU for OCR (if available)"
    )
    TESSERACT_CMD: str = Field(
        default="tesseract",
        description="Path to tesseract executable (default 'tesseract' for system PATH)"
    )
    POPPLER_PATH: str | None = Field(
        default=None, description="Path to poppler bin directory (for PDF conversion)"
    )

    # LLM Configuration (Ollama)
    OLLAMA_HOST: str = Field(
        default="http://localhost:11434", description="Ollama server URL"
    )
    OLLAMA_TIMEOUT: int = Field(
        default=300, description="Ollama request timeout in seconds"
    )
    OLLAMA_MODEL: str = Field(
        default="SpeakLeash/bielik-11b-v2.3-instruct:Q5_K_M", description="Ollama model name"
    )
    TEXT_MODEL: str = Field(
        default="SpeakLeash/bielik-11b-v2.3-instruct:Q5_K_M",
        description="Ollama text model for receipt parsing",
    )
    VISION_MODEL: str = Field(
        default="llava:latest", description="Ollama vision model (if needed)"
    )

    # File Upload Configuration
    MAX_UPLOAD_SIZE: int = Field(
        default=10 * 1024 * 1024,  # 10 MB
        description="Maximum file upload size in bytes",
    )
    UPLOAD_DIR: str = Field(
        default="./data/uploads", description="Directory for uploaded receipt files"
    )
    ALLOWED_EXTENSIONS: List[str] = Field(
        default=[".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".tif"],
        description="Allowed file extensions for uploads",
    )

    # Logging Configuration
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")
    ENABLE_FILE_LOGGING: bool = Field(
        default=False, description="Enable logging to file"
    )
    DEBUG: bool = Field(
        default=False, description="Enable debug mode (e.g. save intermediate images)"
    )

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, list):
            return v
        return v

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"


# Global settings instance
settings = Settings()
