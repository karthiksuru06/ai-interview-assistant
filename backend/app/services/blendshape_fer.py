"""
Blendshape-Based Facial Emotion Recognition
=============================================
Zero-dependency FER using MediaPipe FaceLandmarker blendshapes.
Works without any trained model checkpoint — uses 52 facial action
units from MediaPipe to infer 8 emotion classes.

Also provides Haar cascade face detection (from face_classification repo)
as a lightweight fallback for face ROI extraction.

Source: Ported from frontend FaceAnalyzer.js blendshape-emotion mapping,
enhanced with face_classification repo's detection pipeline.
"""

import logging
import os
import time
import threading
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np

logger = logging.getLogger(__name__)

# MediaPipe Tasks API (modern) — provides blendshapes
try:
    import mediapipe as mp
    from mediapipe.tasks import python as mp_tasks
    from mediapipe.tasks.python import vision as mp_vision
    MEDIAPIPE_TASKS_AVAILABLE = True
except ImportError:
    MEDIAPIPE_TASKS_AVAILABLE = False

EMOTION_LABELS_8 = [
    "neutral", "happiness", "surprise", "sadness",
    "anger", "disgust", "fear", "contempt"
]

# face_classification uses 7 classes (no contempt)
EMOTION_LABELS_7 = [
    "anger", "disgust", "fear", "happiness",
    "sadness", "surprise", "neutral"
]


class HaarCascadeFaceDetector:
    """
    Lightweight face detector using OpenCV Haar Cascade.
    Model file sourced from face_classification repo.
    """

    def __init__(self, cascade_path: Optional[str] = None):
        if cascade_path is None:
            # Try common locations
            candidates = [
                "./models/haarcascade_frontalface_default.xml",
                str(Path(__file__).parent.parent.parent / "models" / "haarcascade_frontalface_default.xml"),
            ]
            for c in candidates:
                if os.path.exists(c):
                    cascade_path = c
                    break

        self.detector = None
        if cascade_path and os.path.exists(cascade_path):
            self.detector = cv2.CascadeClassifier(cascade_path)
            if self.detector.empty():
                self.detector = None
                logger.warning(f"[HAAR] Failed to load cascade from {cascade_path}")
            else:
                logger.info(f"[HAAR] Loaded face cascade from {cascade_path}")
        else:
            # Use OpenCV built-in cascade
            default = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
            if os.path.exists(default):
                self.detector = cv2.CascadeClassifier(default)
                logger.info("[HAAR] Using OpenCV built-in cascade")
            else:
                logger.warning("[HAAR] No Haar cascade found — face detection disabled")

    def detect_faces(
        self,
        image_gray: np.ndarray,
        scale_factor: float = 1.1,
        min_neighbors: int = 5,
        min_size: Tuple[int, int] = (30, 30)
    ) -> List[Tuple[int, int, int, int]]:
        """Detect faces and return list of (x, y, w, h) bounding boxes."""
        if self.detector is None:
            return []

        faces = self.detector.detectMultiScale(
            image_gray,
            scaleFactor=scale_factor,
            minNeighbors=min_neighbors,
            minSize=min_size,
            flags=cv2.CASCADE_SCALE_IMAGE
        )

        if len(faces) == 0:
            return []
        return [tuple(f) for f in faces]

    def extract_face_roi(
        self,
        image: np.ndarray,
        target_size: Tuple[int, int] = (48, 48),
        offset_pct: float = 0.1
    ) -> Optional[np.ndarray]:
        """Extract the largest face ROI, resized to target_size."""
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image

        faces = self.detect_faces(gray)
        if not faces:
            return None

        # Use the largest face
        face = max(faces, key=lambda f: f[2] * f[3])
        x, y, w, h = face

        # Apply offset for more context
        dx = int(w * offset_pct)
        dy = int(h * offset_pct)
        x1 = max(0, x - dx)
        y1 = max(0, y - dy)
        x2 = min(gray.shape[1], x + w + dx)
        y2 = min(gray.shape[0], y + h + dy)

        roi = gray[y1:y2, x1:x2]
        roi = cv2.resize(roi, target_size)

        return roi


class BlendshapeFER:
    """
    Facial Emotion Recognition using MediaPipe FaceLandmarker blendshapes.

    Uses 52 facial action units to compute 8 emotion probabilities.
    No trained model checkpoint needed — runs entirely on MediaPipe.

    Emotion mapping ported from frontend FaceAnalyzer.js and enhanced
    with insights from face_classification repo's emotion categories.
    """

    _instance: Optional["BlendshapeFER"] = None
    _lock = threading.Lock()

    MODEL_URL = (
        "https://storage.googleapis.com/mediapipe-models/"
        "face_landmarker/face_landmarker/float16/1/face_landmarker.task"
    )

    def __new__(cls) -> "BlendshapeFER":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        self.landmarker = None
        self.haar_detector = HaarCascadeFaceDetector()
        self.total_inferences = 0
        self.total_inference_time = 0.0
        self._init_lock = threading.Lock()

        self._try_init_landmarker()

    def _get_model_path(self) -> Optional[str]:
        """Find or download the FaceLandmarker model file."""
        model_dir = Path(__file__).parent.parent.parent / "models"
        model_path = model_dir / "face_landmarker.task"

        if model_path.exists():
            return str(model_path)

        # Try to download
        try:
            import urllib.request
            logger.info(f"[BLENDSHAPE] Downloading FaceLandmarker model...")
            model_dir.mkdir(parents=True, exist_ok=True)
            urllib.request.urlretrieve(self.MODEL_URL, str(model_path))
            logger.info(f"[BLENDSHAPE] Model saved to {model_path}")
            return str(model_path)
        except Exception as e:
            logger.warning(f"[BLENDSHAPE] Failed to download model: {e}")
            return None

    def _try_init_landmarker(self):
        """Initialize MediaPipe FaceLandmarker with blendshapes."""
        if not MEDIAPIPE_TASKS_AVAILABLE:
            logger.warning("[BLENDSHAPE] MediaPipe Tasks API not available")
            return

        model_path = self._get_model_path()
        if model_path is None:
            logger.warning("[BLENDSHAPE] No model file — blendshape FER disabled")
            return

        try:
            # Read model file as bytes to avoid path resolution issues
            with open(model_path, "rb") as f:
                model_data = f.read()

            base_options = mp_tasks.BaseOptions(
                model_asset_buffer=model_data
            )
            options = mp_vision.FaceLandmarkerOptions(
                base_options=base_options,
                running_mode=mp_vision.RunningMode.IMAGE,
                num_faces=1,
                output_face_blendshapes=True,
                output_facial_transformation_matrixes=True,
            )
            self.landmarker = mp_vision.FaceLandmarker.create_from_options(options)
            logger.info("[BLENDSHAPE] FaceLandmarker ready (52 blendshapes)")
        except Exception as e:
            logger.warning(f"[BLENDSHAPE] FaceLandmarker init failed: {e}")
            self.landmarker = None

    @property
    def is_available(self) -> bool:
        return self.landmarker is not None

    def predict(self, image_bgr: np.ndarray) -> Dict:
        """
        Predict emotion from a BGR image using blendshapes.

        Returns dict compatible with InferenceService.predict() format.
        """
        start_time = time.perf_counter()

        if self.landmarker is None:
            return {
                "success": False,
                "error": "BlendshapeFER not initialized"
            }

        try:
            # Convert BGR to RGB for MediaPipe
            image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=image_rgb)

            with self._init_lock:
                result = self.landmarker.detect(mp_image)

            if not result.face_blendshapes or len(result.face_blendshapes) == 0:
                return {
                    "success": True,
                    "emotion": "none",
                    "confidence": 0.0,
                    "all_probabilities": {},
                    "inference_time_ms": round((time.perf_counter() - start_time) * 1000, 2),
                    "source": "blendshape",
                }

            # Extract blendshapes
            bs = {}
            for cat in result.face_blendshapes[0]:
                bs[cat.category_name] = cat.score

            # Map blendshapes to emotions
            emotions = self._blendshapes_to_emotions(bs)

            # Find dominant emotion
            dominant = max(emotions, key=emotions.get)
            confidence = emotions[dominant]

            inference_time = (time.perf_counter() - start_time) * 1000
            self.total_inferences += 1
            self.total_inference_time += inference_time

            return {
                "success": True,
                "emotion": dominant,
                "confidence": confidence,
                "all_probabilities": emotions,
                "inference_time_ms": round(inference_time, 2),
                "source": "blendshape",
            }

        except Exception as e:
            logger.warning(f"[BLENDSHAPE] Prediction error: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def _blendshapes_to_emotions(self, bs: Dict[str, float]) -> Dict[str, float]:
        """
        Map MediaPipe blendshapes to 8 emotion probabilities.

        Uses the same mapping as frontend FaceAnalyzer.js, ported to Python.
        Blendshape reference from mediapipe repo's face_landmarker task.
        """
        # Extract key action units
        smile = bs.get("mouthSmileLeft", 0) + bs.get("mouthSmileRight", 0)
        frown = bs.get("mouthFrownLeft", 0) + bs.get("mouthFrownRight", 0)
        brow_down = bs.get("browDownLeft", 0) + bs.get("browDownRight", 0)
        brow_up = bs.get("browInnerUp", 0)
        jaw_open = bs.get("jawOpen", 0)
        eye_wide = bs.get("eyeWideLeft", 0) + bs.get("eyeWideRight", 0)
        eye_squint = bs.get("eyeSquintLeft", 0) + bs.get("eyeSquintRight", 0)
        mouth_open = bs.get("mouthOpen", 0)
        nose_sneer = bs.get("noseSneerLeft", 0) + bs.get("noseSneerRight", 0)
        mouth_pucker = bs.get("mouthPucker", 0)
        mouth_press = bs.get("mouthPressLeft", 0) + bs.get("mouthPressRight", 0)

        # Compute raw emotion scores
        emotions = {
            "happiness": min(1.0, smile * 0.8 + eye_squint * 0.2),
            "surprise": min(1.0, brow_up * 0.4 + jaw_open * 0.3 + eye_wide * 0.3),
            "sadness": min(1.0, frown * 0.6 + brow_up * 0.2 + max(0, (1 - smile) * 0.2)),
            "anger": min(1.0, brow_down * 0.5 + frown * 0.3 + eye_squint * 0.2),
            "fear": min(1.0, eye_wide * 0.4 + brow_up * 0.3 + mouth_open * 0.3),
            "disgust": min(1.0, nose_sneer * 0.5 + frown * 0.3 + mouth_press * 0.2),
            "contempt": min(1.0, abs(
                bs.get("mouthSmileLeft", 0) - bs.get("mouthSmileRight", 0)
            ) * 2),
        }

        # Neutral = inverse of strongest detected emotion
        max_emotion = max(emotions.values())
        emotions["neutral"] = max(0.0, 1.0 - max_emotion * 1.5)

        # Normalize to sum to 1.0
        total = sum(emotions.values())
        if total > 0:
            emotions = {k: round(v / total, 4) for k, v in emotions.items()}
        else:
            emotions = {k: 0.125 for k in EMOTION_LABELS_8}

        return emotions

    def get_status(self) -> Dict:
        """Get service status."""
        avg_time = (
            self.total_inference_time / self.total_inferences
            if self.total_inferences > 0 else 0.0
        )
        return {
            "available": self.is_available,
            "source": "mediapipe_blendshapes",
            "haar_detector_loaded": self.haar_detector.detector is not None,
            "total_inferences": self.total_inferences,
            "avg_inference_time_ms": round(avg_time, 2),
        }


# Singleton accessor
_blendshape_fer: Optional[BlendshapeFER] = None


def get_blendshape_fer() -> BlendshapeFER:
    """Get the singleton BlendshapeFER instance."""
    global _blendshape_fer
    if _blendshape_fer is None:
        _blendshape_fer = BlendshapeFER()
    return _blendshape_fer
