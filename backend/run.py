"""
Uvicorn Server Runner
=====================
Production-ready server startup script.
"""

import os
import warnings
# Fix for "Descriptors cannot not be created directly" error from protobuf/mediapipe/tensorflow mismatch
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
# Suppress noisy FutureWarnings from google packages
warnings.filterwarnings("ignore", category=FutureWarning, module=r"google\..*")

import uvicorn
from app.config import settings


def main():
    """Run the FastAPI application with uvicorn."""
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        workers=1,  # Single worker for GPU model
        log_level="info",
        access_log=True,
    )


if __name__ == "__main__":
    main()
