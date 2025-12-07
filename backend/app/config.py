"""
Configuration settings for ParagonOCR Web Edition.

Loads environment variables from .env file and provides typed configuration.
"""

import os
from typing import List
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # API Configuration
    API_V1_PREFIX: str = "/api/v1"
    CORS_ORIGINS: List[str] = Field(
        default=["http://localhost:5173", "http://localhost:3000"],
        description="Allowed CORS origins"
    )
    
    # Database Configuration
    DATABASE_URL: str = Field(
        default="sqlite:///./data/receipts.db",
        description="SQLite database URL"
    )
    DATABASE_ECHO: bool = Field(
        default=False,
        description="Echo SQL queries (for debugging)"
    )
    
    # OCR Configuration
    OCR_ENGINE: str = Field(
        default="tesseract",
        description="OCR engine: 'tesseract' or 'easyocr'"
    )
    USE_GPU_OCR: bool = Field(
        default=False,
        description="Use GPU for OCR (if available)"
    )
    TESSERACT_CMD: str = Field(
        default="tesseract",
        description="Path to tesseract executable"
    )
    
    # LLM Configuration (Ollama)
    OLLAMA_HOST: str = Field(
        default="http://localhost:11434",
        description="Ollama server URL"
    )
    OLLAMA_TIMEOUT: int = Field(
        default=300,
        description="Ollama request timeout in seconds"
    )
    TEXT_MODEL: str = Field(
        default="bielik-4.5b-v3.0-instruct:Q4_K_M",
        description="Ollama text model for receipt parsing"
    )
    VISION_MODEL: str = Field(
        default="llava:latest",
        description="Ollama vision model (if needed)"
    )
    
    # File Upload Configuration
    MAX_UPLOAD_SIZE: int = Field(
        default=10 * 1024 * 1024,  # 10 MB
        description="Maximum file upload size in bytes"
    )
    UPLOAD_DIR: str = Field(
        default="./data/uploads",
        description="Directory for uploaded receipt files"
    )
    ALLOWED_EXTENSIONS: List[str] = Field(
        default=[".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".tif"],
        description="Allowed file extensions for uploads"
    )
    
    # Logging Configuration
    LOG_LEVEL: str = Field(
        default="INFO",
        description="Logging level"
    )
    ENABLE_FILE_LOGGING: bool = Field(
        default=False,
        description="Enable logging to file"
    )
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()

