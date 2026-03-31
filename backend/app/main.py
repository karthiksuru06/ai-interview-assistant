"""
Main Entry Point
=================
FastAPI application factory — wires CORS, lifecycle events, and routers.
"""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_database, close_database
from app.routers import auth, history, interview, health, admin

# Inference service (for model loading)
try:
    from app.services.inference import get_inference_service
    _inference_available = True
except Exception:
    _inference_available = False

# Multimodal router is optional (requires extra services)
try:
    from app.routers import multimodal as multimodal_router_module
    _multimodal_available = True
except Exception:
    _multimodal_available = False

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Smart AI Interview Assistant",
    version="1.0.0",
    description="Backend API — FastAPI + SQLite",
)

# ---------------------------------------------------------------------------
# CORS — allow all localhost ports during development
# ---------------------------------------------------------------------------
_cors_origins = list(settings.cors_origins)
# Auto-add common localhost dev ports so Vite port changes don't break CORS
for port in range(3000, 3010):
    origin = f"http://localhost:{port}"
    if origin not in _cors_origins:
        _cors_origins.append(origin)
for port in range(5173, 5180):
    origin = f"http://localhost:{port}"
    if origin not in _cors_origins:
        _cors_origins.append(origin)
    origin_127 = f"http://127.0.0.1:{port}"
    if origin_127 not in _cors_origins:
        _cors_origins.append(origin_127)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Warn if CORS is still set to localhost-only defaults
_all_localhost = all("localhost" in o or "127.0.0.1" in o for o in settings.cors_origins)
if _all_localhost:
    logging.getLogger(__name__).warning(
        "CORS origins are localhost-only. Set CORS_ORIGINS in .env for production "
        "(e.g. CORS_ORIGINS='[\"https://app.yoursite.com\"]')"
    )

# ---------------------------------------------------------------------------
# Lifecycle events
# ---------------------------------------------------------------------------

@app.on_event("startup")
async def startup_event():
    logger.info("Starting up ...")
    await init_database()
    await auth.ensure_admin_user()

    # Load AI Model
    if _inference_available:
        logger.info("Loading AI models...")
        import asyncio
        service = get_inference_service()
        model_loaded = await asyncio.to_thread(service.load_model)

        if not model_loaded:
            logger.warning(
                "PyTorch FER model not found. "
                "Using blendshape-based emotion detection (MediaPipe FaceLandmarker) as fallback."
            )
            # Blendshape FER is auto-initialized in InferenceService.__init__
            if service.blendshape_fer and service.blendshape_fer.is_available:
                logger.info("Blendshape FER fallback is ACTIVE — emotion detection will work.")
            else:
                logger.warning(
                    "Blendshape FER also unavailable. Emotion detection disabled. "
                    "Run: python scripts/convert_keras_model.py to generate a model."
                )

    logger.info("Startup complete.")


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down ...")
    await close_database()
    logger.info("Shutdown complete.")


# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(auth.router)
app.include_router(history.router)
app.include_router(interview.router)
app.include_router(health.router)
app.include_router(admin.router)

if _multimodal_available:
    app.include_router(multimodal_router_module.router)
    logger.info("multimodal.router included.")
else:
    logger.warning(
        "multimodal.router could NOT be imported (missing service dependencies). "
        "Core endpoints (auth, interview, history, health) are fully operational."
    )


@app.get("/")
async def root():
    return {
        "message": "Smart AI Interview Assistant API is running",
        "docs": "/docs",
    }
