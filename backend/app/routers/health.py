"""
Health Check Router
====================
Endpoints for monitoring service health and status.
"""

from fastapi import APIRouter

from app.config import settings
from app import database as db
from app.schemas import HealthCheck, InferenceStatus

# PyTorch is optional — may not be installed or may be CPU-only
try:
    import torch
    _torch_available = True
except ImportError:
    torch = None
    _torch_available = False

# Inference service is optional
try:
    from app.services import get_inference_service
    _inference_available = True
except Exception:
    _inference_available = False

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("", response_model=HealthCheck)
async def health_check() -> HealthCheck:
    """
    Comprehensive health check endpoint.
    Returns status of GPU, model, and database connectivity.
    """
    gpu_available = torch.cuda.is_available() if _torch_available else False
    gpu_name = torch.cuda.get_device_name(0) if gpu_available else None

    model_loaded = False
    fer_active = False
    if _inference_available:
        inference_service = get_inference_service()
        model_loaded = inference_service.model is not None
        # FER is active if either PyTorch model OR blendshape fallback works
        fer_active = model_loaded or (
            inference_service.blendshape_fer is not None
            and inference_service.blendshape_fer.is_available
        )

    # Check database connectivity
    db_connected = db.users_collection is not None

    return HealthCheck(
        status="healthy" if db_connected else "degraded",
        version=settings.app_version,
        gpu_available=gpu_available,
        gpu_name=gpu_name,
        model_loaded=model_loaded or fer_active,
        database_connected=db_connected,
    )


@router.get("/inference", response_model=InferenceStatus)
async def inference_status() -> InferenceStatus:
    """Get detailed inference service status."""
    if not _inference_available:
        return InferenceStatus(
            model_loaded=False,
            device="cpu",
            model_architecture=settings.fer_model_architecture,
            warm=False,
            total_inferences=0,
            avg_inference_time_ms=0.0,
        )

    service = get_inference_service()
    status = service.get_status()
    return InferenceStatus(**status)


@router.get("/gpu")
async def gpu_info():
    """Get detailed GPU information."""
    if not _torch_available or not torch.cuda.is_available():
        return {"available": False, "message": "CUDA not available"}

    props = torch.cuda.get_device_properties(0)

    return {
        "available": True,
        "device_name": torch.cuda.get_device_name(0),
        "cuda_version": torch.version.cuda,
        "cudnn_version": torch.backends.cudnn.version(),
        "total_memory_gb": round(props.total_memory / (1024**3), 2),
        "allocated_memory_gb": round(torch.cuda.memory_allocated(0) / (1024**3), 2),
        "cached_memory_gb": round(torch.cuda.memory_reserved(0) / (1024**3), 2),
        "compute_capability": f"{props.major}.{props.minor}",
        "multi_processor_count": props.multi_processor_count,
    }
