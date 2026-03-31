"""
Services Module
===============
Core services for the Smart AI Interview Assistant.
"""

from app.services.inference import InferenceService, get_inference_service
from app.services.gemini import GeminiService, get_gemini_service
from app.services.audio import AudioService, get_audio_service
from app.services.audio_inference import AudioInferenceService, get_audio_inference_service
from app.services.metrics import MetricsCalculator, get_metrics_calculator
from app.services.blendshape_fer import BlendshapeFER, get_blendshape_fer

__all__ = [
    # Inference (FER Model - Video)
    "InferenceService",
    "get_inference_service",

    # Blendshape FER Fallback (from face_classification + mediapipe repos)
    "BlendshapeFER",
    "get_blendshape_fer",

    # Inference (Audio Emotion)
    "AudioInferenceService",
    "get_audio_inference_service",

    # Gemini AI
    "GeminiService",
    "get_gemini_service",

    # Audio Processing (Signal Analysis)
    "AudioService",
    "get_audio_service",

    # Metrics Calculator
    "MetricsCalculator",
    "get_metrics_calculator"
]
