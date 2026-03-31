"""
FER Service
===========
Provides facial emotion recognition using the 'fer' library.
Suggested by user's friend as a lightweight, real-time fallback.
"""

import logging
import time
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np

try:
    from fer import FER
    FER_AVAILABLE = True
except ImportError:
    FER_AVAILABLE = False

from app.config import settings

logger = logging.getLogger(__name__)

class FERService:
    """
    Facial Emotion Recognition using the FER library.
    
    This is a wrapper around the FER model which uses MTCNN or Haar Cascades
    for face detection and a pre-trained Keras model for emotion classification.
    """

    _instance: Optional["FERService"] = None

    def __new__(cls, *args, **kwargs) -> "FERService":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, use_mtcnn: bool = False):
        if self._initialized:
            return
        
        self.detector = None
        if FER_AVAILABLE:
            try:
                # mtcnn=True is more accurate but slower. Default to False for real-time.
                self.detector = FER(mtcnn=use_mtcnn)
                logger.info(f"[FER_SERVICE] Initialized (mtcnn={use_mtcnn})")
            except Exception as e:
                logger.error(f"[FER_SERVICE] Failed to initialize: {e}")
        else:
            logger.warning("[FER_SERVICE] 'fer' library not installed")
            
        self._initialized = True
        self.total_inferences = 0
        self.total_inference_time = 0.0

    @property
    def is_available(self) -> bool:
        return self.detector is not None

    def predict(self, image_bgr: np.ndarray) -> Dict:
        """
        Predict emotion from a BGR image.
        Returns dict compatible with InferenceService.predict() format.
        """
        start_time = time.perf_counter()

        if self.detector is None:
            return {
                "success": False,
                "error": "FER detector not initialized"
            }

        try:
            # FER.detect_emotions expects BGR images (OpenCV default)
            result = self.detector.detect_emotions(image_bgr)

            if not result:
                return {
                    "success": True,
                    "emotion": "neutral",
                    "confidence": 0.5,
                    "all_probabilities": {"neutral": 0.5},
                    "inference_time_ms": round((time.perf_counter() - start_time) * 1000, 2),
                    "source": "fer_library",
                }

            # Use the first face detected
            face_data = result[0]
            emotions = face_data["emotions"]
            dominant = max(emotions, key=emotions.get)
            confidence = emotions[dominant]
            box = face_data.get("box", [])

            inference_time = (time.perf_counter() - start_time) * 1000
            self.total_inferences += 1
            self.total_inference_time += inference_time

            return {
                "success": True,
                "emotion": dominant,
                "confidence": round(float(confidence), 4),
                "all_probabilities": {k: round(float(v), 4) for k, v in emotions.items()},
                "box": box, # [x, y, w, h]
                "inference_time_ms": round(inference_time, 2),
                "source": "fer_library",
            }

        except Exception as e:
            logger.warning(f"[FER_SERVICE] Prediction error: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def get_status(self) -> Dict:
        avg_time = (
            self.total_inference_time / self.total_inferences
            if self.total_inferences > 0 else 0.0
        )
        return {
            "available": self.is_available,
            "source": "fer_library",
            "total_inferences": self.total_inferences,
            "avg_inference_time_ms": round(avg_time, 2),
        }

# Singleton accessor
_fer_service: Optional[FERService] = None

def get_fer_service() -> FERService:
    global _fer_service
    if _fer_service is None:
        _fer_service = FERService(use_mtcnn=settings.fer_use_mtcnn)
    return _fer_service
