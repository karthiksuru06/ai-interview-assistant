"""
Application Configuration
=========================
Centralized configuration management with environment variable support.

Authentication: JWT (python-jose) + passlib (pbkdf2_sha256) + SQLite.
"""

import secrets
import warnings
from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # Application
    app_name: str = "Smart AI Interview Assistant"
    app_version: str = "1.0.0"
    debug: bool = False

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # FER (Facial Emotion Recognition)
    fer_model_path: str = "models/best_model.pth"
    fer_model_architecture: str = "efficientnet_b0"  # Options: resnet50, efficientnet_b0
    fer_use_mtcnn: bool = False  # Set to True for better accuracy (friend's suggestion) but slower
    fer_num_classes: int = 8

    # Gemini AI
    gemini_api_key: Optional[str] = None
    gemini_model: str = "gemini-2.5-flash"

    # Inference settings
    inference_device: str = "cpu"  # "cuda" or "cpu"
    inference_image_size: int = 224
    max_batch_size: int = 4

    # WebSocket settings
    ws_max_frame_size: int = 1048576  # 1MB
    ws_heartbeat_interval: int = 30

    # CORS (for frontend)
    # Override via env: CORS_ORIGINS='["https://app.yoursite.com"]'
    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
    ]

    # JWT Authentication
    jwt_secret_key: str = "your-super-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24  # 24 hours

    # Admin credentials (override via .env for production)
    admin_email: str = "admin@smartai.com"
    admin_password: str = "admin"

    # Rate limiting
    rate_limit_login_per_minute: int = 10
    rate_limit_signup_per_minute: int = 5
    rate_limit_transcribe_per_minute: int = 20

    # AI Safe Mode — when False, all AI components MUST use real inference.
    # Fallback/mock responses are disabled and errors are raised explicitly.
    ai_safe_mode: bool = True

    # Database
    mongodb_uri: str = ""  # Set full MongoDB URI in .env (e.g. mongodb+srv://user:pass@host/)
    use_mongodb: bool = True


_INSECURE_DEFAULT_SECRET = "your-super-secret-key-change-in-production"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    s = Settings()

    # Warn (and auto-generate in dev) if JWT secret is the insecure default
    if s.jwt_secret_key == _INSECURE_DEFAULT_SECRET:
        generated = secrets.token_urlsafe(48)
        warnings.warn(
            "\n"
            "  !! JWT_SECRET_KEY is the insecure default.\n"
            f"  !! Auto-generated a random secret for this process: {generated[:12]}...\n"
            "  !! Set JWT_SECRET_KEY in .env for production!\n",
            stacklevel=2,
        )
        # Mutate the instance so the rest of the app uses the generated secret
        object.__setattr__(s, "jwt_secret_key", generated)

    return s


settings = get_settings()
