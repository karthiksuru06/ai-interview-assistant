"""
Inference Service
=================
Singleton PyTorch model service for real-time facial emotion recognition,
head pose estimation (MediaPipe), and iris gaze tracking.
Optimized for NVIDIA RTX 4060 with CUDA acceleration.
"""

import base64
import io
import logging
import time
from typing import Dict, List, Optional, Tuple
import threading

import cv2
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from PIL import Image
from torchvision import models, transforms
from torchvision.models import EfficientNet_B0_Weights, ResNet50_Weights

from app.config import settings

logger = logging.getLogger(__name__)

# MediaPipe is optional — graceful degradation if not installed
try:
    import mediapipe as mp
    MEDIAPIPE_AVAILABLE = True
except ImportError:
    MEDIAPIPE_AVAILABLE = False
    mp = None

# Blendshape-based FER fallback (uses face_classification + mediapipe repos)
try:
    from app.services.blendshape_fer import get_blendshape_fer, BlendshapeFER
    BLENDSHAPE_FER_AVAILABLE = True
except ImportError:
    BLENDSHAPE_FER_AVAILABLE = False

# FER-library based fallback (user's friend suggestion)
try:
    from app.services.fer_service import get_fer_service, FERService
    FER_LIBRARY_AVAILABLE = True
except ImportError:
    FER_LIBRARY_AVAILABLE = False


class FERModel(nn.Module):
    """
    Facial Emotion Recognition model architecture.
    Must match the architecture used during training.
    """

    SUPPORTED_ARCHITECTURES = ["resnet50", "efficientnet_b0"]

    def __init__(
        self,
        architecture: str = "efficientnet_b0",
        num_classes: int = 8,
        dropout_rate: float = 0.5
    ):
        super().__init__()

        self.architecture = architecture.lower()

        if self.architecture == "resnet50":
            backbone = models.resnet50(weights=None)
            self.feature_dim = backbone.fc.in_features
            backbone.fc = nn.Identity()

        elif self.architecture == "efficientnet_b0":
            backbone = models.efficientnet_b0(weights=None)
            self.feature_dim = backbone.classifier[1].in_features
            backbone.classifier = nn.Identity()

        else:
            raise ValueError(f"Unsupported architecture: {architecture}")

        self.backbone = backbone
        self.classifier = nn.Sequential(
            nn.Dropout(p=dropout_rate),
            nn.Linear(self.feature_dim, 512),
            nn.BatchNorm1d(512),
            nn.ReLU(inplace=True),
            nn.Dropout(p=dropout_rate * 0.5),
            nn.Linear(512, num_classes)
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        features = self.backbone(x)
        return self.classifier(features)


class MediaPipeAnalyzer:
    """
    Head pose estimation (Yaw/Pitch/Roll) and iris gaze tracking
    using MediaPipe Face Mesh with 478 landmarks.

    Posture rules:
        Pitch > 15°   → "Slouching"
        |Yaw| > 25°   → "Looking Away"
        otherwise      → "Good"

    Eye-contact rules:
        Iris deviation > 20% from center for > 5 sec → "Distracted"
        otherwise → "Center" / "Left" / "Right"
    """

    # 3D model points for solvePnP (standard face model, mm scale)
    MODEL_POINTS_3D = np.array([
        (0.0, 0.0, 0.0),           # Nose tip
        (0.0, -330.0, -65.0),      # Chin
        (-225.0, 170.0, -135.0),   # Left eye outer corner
        (225.0, 170.0, -135.0),    # Right eye outer corner
        (-150.0, -150.0, -125.0),  # Left mouth corner
        (150.0, -150.0, -125.0),   # Right mouth corner
    ], dtype=np.float64)

    # Face Mesh landmark indices matching the 3D model points above
    POSE_LANDMARK_IDS = [1, 152, 33, 263, 61, 291]

    # Iris landmarks (requires refine_landmarks=True)
    LEFT_IRIS_CENTER = 468
    RIGHT_IRIS_CENTER = 473
    LEFT_EYE_INNER = 133
    LEFT_EYE_OUTER = 33
    RIGHT_EYE_INNER = 362
    RIGHT_EYE_OUTER = 263

    # Thresholds (tuned to reduce false positives)
    PITCH_SLOUCH_DEG = 20.0     # was 15° — too sensitive for normal head tilt
    YAW_AWAY_DEG = 30.0         # was 25° — give more leeway before "Looking Away"
    GAZE_DEVIATION_PCT = 0.22   # 22% off-center (slightly more forgiving)
    DISTRACTION_SEC = 5.0       # seconds off-center → "Distracted"
    NO_FACE_GRACE_SEC = 0.3     # grace period before reporting "No Face"

    def __init__(self):
        if not MEDIAPIPE_AVAILABLE:
            self.face_mesh = None
            logger.warning("[MEDIAPIPE] Not installed — posture/gaze analysis disabled")
            return

        try:
            self.face_mesh = mp.solutions.face_mesh.FaceMesh(
                static_image_mode=False,
                max_num_faces=1,
                refine_landmarks=True,      # enables 10 iris landmarks
                min_detection_confidence=0.6,
                min_tracking_confidence=0.55,
            )
            logger.info("[MEDIAPIPE] Face Mesh initialised (478 landmarks, iris tracking ON)")
        except (AttributeError, Exception) as e:
            self.face_mesh = None
            logger.error(f"[MEDIAPIPE] Initialization failed: {e}. Posture analysis disabled.")

        # Temporal gaze-distraction state
        self._gaze_off_start: Optional[float] = None
        # Grace period state for face loss (prevents flicker)
        self._no_face_start: Optional[float] = None
        self._last_good_result: Optional[Dict] = None

    # ── public API ──────────────────────────────────────────────────────

    def analyze(self, image_bgr: np.ndarray) -> Dict:
        """
        Run head-pose + iris-gaze on a single BGR frame.

        Returns:
            {
                "posture": "Good" | "Slouching" | "Looking Away" | "No Face",
                "eye_contact": "Center" | "Left" | "Right" | "Distracted" | "No Face",
                "head_pose": {"yaw": float, "pitch": float, "roll": float} | None,
                "gaze_ratio": float   # 0.0=far-left  0.5=center  1.0=far-right
            }
        """
        if self.face_mesh is None:
            return self._default()

        h, w = image_bgr.shape[:2]
        rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
        results = self.face_mesh.process(rgb)

        if not results.multi_face_landmarks:
            now = time.time()
            # Grace period: return last known good result briefly
            if self._no_face_start is None:
                self._no_face_start = now
            if (now - self._no_face_start) < self.NO_FACE_GRACE_SEC and self._last_good_result:
                return self._last_good_result
            # Grace period expired — report no face
            self._gaze_off_start = None
            return {"posture": "No Face", "eye_contact": "No Face",
                    "head_pose": None, "gaze_ratio": 0.5}

        # Face detected — reset grace timer
        self._no_face_start = None

        lm = results.multi_face_landmarks[0].landmark

        head_pose = self._head_pose(lm, w, h)
        posture = self._classify_posture(head_pose)
        gaze_ratio = self._iris_gaze_ratio(lm, w)
        eye_contact = self._classify_gaze(gaze_ratio)

        # Geometric emotion detection (fallback FER using landmarks)
        geo_emotion = self.detect_emotion_geometric(lm, w, h)

        result = {
            "posture": posture,
            "eye_contact": eye_contact,
            "head_pose": head_pose,
            "gaze_ratio": round(gaze_ratio, 3),
            "_geo_emotion": geo_emotion,  # Used by InferenceService fallback
        }
        self._last_good_result = result
        return result

    # ── head pose ───────────────────────────────────────────────────────

    def _head_pose(self, lm, w: int, h: int) -> Dict:
        """solvePnP → Euler angles (yaw, pitch, roll in degrees)."""
        image_pts = np.array(
            [(lm[i].x * w, lm[i].y * h) for i in self.POSE_LANDMARK_IDS],
            dtype=np.float64,
        )

        focal = float(w)
        cam_matrix = np.array([
            [focal, 0, w / 2],
            [0, focal, h / 2],
            [0, 0, 1],
        ], dtype=np.float64)

        ok, rvec, _ = cv2.solvePnP(
            self.MODEL_POINTS_3D, image_pts, cam_matrix,
            np.zeros((4, 1), dtype=np.float64),
            flags=cv2.SOLVEPNP_ITERATIVE,
        )
        if not ok:
            return {"yaw": 0.0, "pitch": 0.0, "roll": 0.0}

        rmat, _ = cv2.Rodrigues(rvec)
        sy = np.sqrt(rmat[0, 0] ** 2 + rmat[1, 0] ** 2)

        if sy > 1e-6:
            pitch = np.degrees(np.arctan2(rmat[2, 1], rmat[2, 2]))
            yaw = np.degrees(np.arctan2(-rmat[2, 0], sy))
            roll = np.degrees(np.arctan2(rmat[1, 0], rmat[0, 0]))
        else:
            pitch = np.degrees(np.arctan2(-rmat[1, 2], rmat[1, 1]))
            yaw = np.degrees(np.arctan2(-rmat[2, 0], sy))
            roll = 0.0

        return {
            "yaw": round(float(yaw), 1),
            "pitch": round(float(pitch), 1),
            "roll": round(float(roll), 1),
        }

    def _classify_posture(self, pose: Dict) -> str:
        pitch = pose.get("pitch", 0.0)
        yaw = abs(pose.get("yaw", 0.0))
        if pitch > self.PITCH_SLOUCH_DEG:
            return "Slouching"
        if yaw > self.YAW_AWAY_DEG:
            return "Looking Away"
        return "Good"

    # ── iris gaze ───────────────────────────────────────────────────────

    def _iris_gaze_ratio(self, lm, w: int) -> float:
        """
        Horizontal iris position averaged over both eyes.
        Returns 0.0 (far left) … 0.5 (center) … 1.0 (far right).
        """
        def _eye_ratio(iris_idx, inner_idx, outer_idx):
            ix = lm[iris_idx].x * w
            inner_x = lm[inner_idx].x * w
            outer_x = lm[outer_idx].x * w
            width = abs(inner_x - outer_x)
            if width < 1:
                return 0.5
            return (ix - min(inner_x, outer_x)) / width

        left = _eye_ratio(self.LEFT_IRIS_CENTER,
                          self.LEFT_EYE_INNER, self.LEFT_EYE_OUTER)
        right = _eye_ratio(self.RIGHT_IRIS_CENTER,
                           self.RIGHT_EYE_INNER, self.RIGHT_EYE_OUTER)
        return (left + right) / 2.0

    def _classify_gaze(self, ratio: float) -> str:
        """Classify gaze with 5-second distraction timer."""
        deviation = abs(ratio - 0.5)
        now = time.time()

        if deviation > self.GAZE_DEVIATION_PCT:
            if self._gaze_off_start is None:
                self._gaze_off_start = now
            if (now - self._gaze_off_start) >= self.DISTRACTION_SEC:
                return "Distracted"
            return "Left" if ratio < 0.3 else ("Right" if ratio > 0.7 else "Center")
        else:
            self._gaze_off_start = None
            return "Center"

    # ── geometric emotion detection ────────────────────────────────────
    # Ported from frontend FaceAnalyzer.js + face_classification repo.
    # Uses 478 Face Mesh landmarks to infer emotions without any model.

    # Landmark indices for emotion detection
    _UPPER_LIP = 13
    _LOWER_LIP = 14
    _LEFT_MOUTH = 61
    _RIGHT_MOUTH = 291
    _LEFT_EYEBROW_INNER = 107
    _RIGHT_EYEBROW_INNER = 336
    _LEFT_EYEBROW_OUTER = 70
    _RIGHT_EYEBROW_OUTER = 300
    _LEFT_EYE_TOP = 159
    _LEFT_EYE_BOTTOM = 145
    _RIGHT_EYE_TOP = 386
    _RIGHT_EYE_BOTTOM = 374

    def detect_emotion_geometric(self, lm, w: int, h: int) -> Dict:
        """
        Infer emotion from facial landmark geometry (no model needed).
        Returns dict with emotion, confidence, all_probabilities.
        """
        try:
            # Mouth metrics
            mouth_w = abs(lm[self._RIGHT_MOUTH].x - lm[self._LEFT_MOUTH].x) * w
            mouth_h = abs(lm[self._LOWER_LIP].y - lm[self._UPPER_LIP].y) * h
            mouth_ratio = mouth_h / max(mouth_w, 1)

            # Smile detection: corners relative to center
            mouth_cy = (lm[self._UPPER_LIP].y + lm[self._LOWER_LIP].y) / 2
            l_corner_up = mouth_cy - lm[self._LEFT_MOUTH].y
            r_corner_up = mouth_cy - lm[self._RIGHT_MOUTH].y
            smile = (l_corner_up + r_corner_up) / 2

            # Eyebrow height
            l_brow = lm[self._LEFT_EYE_TOP].y - lm[self._LEFT_EYEBROW_INNER].y
            r_brow = lm[self._RIGHT_EYE_TOP].y - lm[self._RIGHT_EYEBROW_INNER].y
            brow_h = (l_brow + r_brow) / 2

            # Brow furrow (anger)
            brow_furrow = (
                (lm[self._LEFT_EYEBROW_OUTER].y - lm[self._LEFT_EYEBROW_INNER].y) +
                (lm[self._RIGHT_EYEBROW_OUTER].y - lm[self._RIGHT_EYEBROW_INNER].y)
            ) / 2

            # Eye openness
            eye_open = (
                abs(lm[self._LEFT_EYE_TOP].y - lm[self._LEFT_EYE_BOTTOM].y) +
                abs(lm[self._RIGHT_EYE_TOP].y - lm[self._RIGHT_EYE_BOTTOM].y)
            ) / 2

            # Smile asymmetry (contempt)
            smile_asym = abs(l_corner_up - r_corner_up)

            # Raw emotion scores
            emo = {
                "happiness": min(1.0, max(0, smile * 12 + 0.1) * 0.8 + max(0, 0.03 - eye_open) * 5 * 0.2),
                "surprise": min(1.0, max(0, brow_h - 0.03) * 8 * 0.4 + max(0, eye_open - 0.025) * 10 * 0.3 + mouth_ratio * 0.3),
                "sadness": min(1.0, max(0, -smile * 10) * 0.6 + max(0, brow_h - 0.025) * 6 * 0.4),
                "anger": min(1.0, max(0, brow_furrow + 0.01) * 8 * 0.5 + max(0, -smile * 8) * 0.3 + max(0, 0.02 - mouth_ratio) * 10 * 0.2),
                "fear": min(1.0, max(0, eye_open - 0.03) * 8 * 0.4 + max(0, brow_h - 0.035) * 6 * 0.3 + mouth_ratio * 0.3),
                "disgust": min(1.0, max(0, -smile * 6) * 0.5 + max(0, brow_furrow) * 5 * 0.5),
                "contempt": min(1.0, smile_asym * 15),
            }

            # Neutral = inverse of max
            max_emo = max(emo.values())
            emo["neutral"] = max(0.0, 1.0 - max_emo * 1.5)

            # Normalize
            total = sum(emo.values())
            if total > 0:
                emo = {k: round(v / total, 4) for k, v in emo.items()}
            else:
                emo = {k: 0.125 for k in emo}

            dominant = max(emo, key=emo.get)
            return {
                "emotion": dominant,
                "confidence": emo[dominant],
                "all_probabilities": emo,
                "source": "geometric_landmarks",
            }
        except Exception as e:
            logger.warning(f"[MEDIAPIPE] Geometric emotion error: {e}")
            return {
                "emotion": "neutral",
                "confidence": 0.5,
                "all_probabilities": {"neutral": 1.0},
                "source": "geometric_fallback",
            }

    # ── helpers ─────────────────────────────────────────────────────────

    @staticmethod
    def _default() -> Dict:
        return {"posture": "Unknown", "eye_contact": "Unknown",
                "head_pose": None, "gaze_ratio": 0.5}


class InferenceService:
    """
    Singleton service for FER model inference + MediaPipe posture/gaze.

    Loads the model once at startup and provides thread-safe predictions.
    Optimized for GPU inference with the RTX 4060.
    """

    EMOTION_LABELS = [
        "neutral", "happiness", "surprise", "sadness",
        "anger", "disgust", "fear", "contempt"
    ]

    _instance: Optional["InferenceService"] = None
    _lock = threading.Lock()

    def __new__(cls) -> "InferenceService":
        """Ensure singleton pattern."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize the inference service (only once)."""
        if self._initialized:
            return

        self._initialized = True
        self.model: Optional[nn.Module] = None
        self.device: torch.device = torch.device("cpu")
        self.transform: Optional[transforms.Compose] = None

        # MediaPipe analyzer for posture + gaze (works independently of FER)
        self.mediapipe_analyzer: Optional[MediaPipeAnalyzer] = None
        if MEDIAPIPE_AVAILABLE:
            self.mediapipe_analyzer = MediaPipeAnalyzer()

        # FER-library based fallback (user's friend suggestion)
        self.fer_library_service: Optional[FERService] = None
        if FER_LIBRARY_AVAILABLE:
            try:
                self.fer_library_service = get_fer_service()
                logger.info("[INFERENCE] FER-library service available")
            except Exception as e:
                logger.error(f"[INFERENCE] FER-library init failed: {e}")

        # Blendshape-based FER fallback
        self.blendshape_fer: Optional[BlendshapeFER] = None

        # Statistics
        self.total_inferences: int = 0
        self.total_inference_time: float = 0.0
        self.is_warm: bool = False

        # Initialize
        self._setup_device()
        self._setup_transform()

    def _setup_device(self) -> None:
        """Configure compute device (GPU/CPU)."""
        if settings.inference_device == "cuda" and torch.cuda.is_available():
            self.device = torch.device("cuda")
            gpu_name = torch.cuda.get_device_name(0)
            vram = torch.cuda.get_device_properties(0).total_memory / (1024**3)
            logger.info(f"[INFERENCE] GPU detected: {gpu_name} ({vram:.1f} GB)")
            logger.info(f"[INFERENCE] CUDA version: {torch.version.cuda}")

            # Enable optimizations
            torch.backends.cudnn.benchmark = True

        else:
            self.device = torch.device("cpu")
            logger.info("[INFERENCE] Running on CPU (GPU not available)")

    def _setup_transform(self) -> None:
        """Setup image preprocessing pipeline."""
        self.transform = transforms.Compose([
            transforms.Resize((settings.inference_image_size, settings.inference_image_size)),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=[0.485, 0.456, 0.406],
                std=[0.229, 0.224, 0.225]
            )
        ])

    def load_model(self, model_path: Optional[str] = None) -> bool:
        """
        Load the trained FER model from disk.

        Args:
            model_path: Path to the model checkpoint. Uses settings default if None.

        Returns:
            True if model loaded successfully, False otherwise.
        """
        path = model_path or settings.fer_model_path

        try:
            logger.info(f"[INFERENCE] Loading model from: {path}")

            # Create model architecture
            self.model = FERModel(
                architecture=settings.fer_model_architecture,
                num_classes=settings.fer_num_classes
            )

            # Load checkpoint (always map to current device to handle CUDA→CPU)
            checkpoint = torch.load(path, map_location=self.device, weights_only=False)

            # Handle different checkpoint formats
            if isinstance(checkpoint, dict):
                if "model_state_dict" in checkpoint:
                    self.model.load_state_dict(checkpoint["model_state_dict"])
                    logger.info(f"[INFERENCE] Loaded from epoch {checkpoint.get('epoch', '?')}")
                    logger.info(f"[INFERENCE] Val accuracy: {checkpoint.get('val_acc', '?')}")
                else:
                    self.model.load_state_dict(checkpoint)
            else:
                self.model.load_state_dict(checkpoint)

            # Move to device and set eval mode
            self.model = self.model.to(self.device)
            self.model.eval()

            logger.info(f"[INFERENCE] Model loaded successfully on {self.device}")
            return True

        except FileNotFoundError:
            logger.warning(f"[INFERENCE] Model file not found: {path}")
            return False
        except Exception as e:
            logger.error(f"[INFERENCE] Error loading model: {e}")
            return False

    def _preprocess_image(self, image: np.ndarray) -> torch.Tensor:
        """
        Preprocess image for model input.

        Args:
            image: BGR or RGB numpy array

        Returns:
            Preprocessed tensor ready for inference
        """
        # Ensure RGB format
        if len(image.shape) == 2:
            image = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
        elif image.shape[2] == 4:
            image = cv2.cvtColor(image, cv2.COLOR_BGRA2RGB)
        elif image.shape[2] == 3:
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        # Convert to PIL for transforms
        pil_image = Image.fromarray(image)

        # Apply transforms
        tensor = self.transform(pil_image)

        return tensor.unsqueeze(0)  # Add batch dimension

    def decode_base64_frame(self, base64_string: str) -> np.ndarray:
        """
        Decode Base64 encoded image to numpy array.

        Args:
            base64_string: Base64 encoded image string

        Returns:
            Decoded image as numpy array (BGR format)
        """
        # Remove data URL prefix if present
        if "base64," in base64_string:
            base64_string = base64_string.split("base64,")[1]

        # Decode
        image_bytes = base64.b64decode(base64_string)
        image_array = np.frombuffer(image_bytes, dtype=np.uint8)
        image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)

        if image is None:
            raise ValueError("Failed to decode image from Base64")

        return image

    _mp_lock = threading.Lock()

    def _run_mediapipe(self, image: np.ndarray) -> Dict:
        """Run MediaPipe analysis (posture + gaze). Thread-safe via lock."""
        mp_defaults = {"posture": "Unknown", "eye_contact": "Unknown",
                       "head_pose": None, "gaze_ratio": 0.5}
        if self.mediapipe_analyzer is None:
            return mp_defaults
        try:
            with self._mp_lock:
                return self.mediapipe_analyzer.analyze(image)
        except Exception as e:
            logger.warning(f"[MEDIAPIPE] Analysis error: {e}")
            return mp_defaults

    @torch.no_grad()
    def predict(self, image: np.ndarray) -> Dict:
        """
        Run emotion prediction + posture/gaze analysis on an image.

        Args:
            image: Input image (BGR numpy array)

        Returns:
            Dictionary with emotion, posture, eye_contact, head_pose, gaze_ratio
        """
        if image is None:
            return {"success": False, "error": "no_frame", "emotion": "none", "confidence": 0.0}

        start_time = time.perf_counter()

        # MediaPipe runs independently of FER model
        mp_data = self._run_mediapipe(image)

        # If no face is detected, strictly return 'none' to avoid hallucinations
        if not mp_data or mp_data.get("posture") == "No Face" or mp_data.get("eye_contact") == "No Face":
            return {
                "success": True,
                "emotion": "none",
                "confidence": 0.0,
                "all_probabilities": {},
                "inference_time_ms": round((time.perf_counter() - start_time) * 1000, 2),
                **mp_data,
            }

        if self.model is None:
            # Fallback 1: FER-library based (user's friend suggestion)
            if self.fer_library_service and self.fer_library_service.is_available:
                fer_result = self.fer_library_service.predict(image)
                if fer_result.get("success"):
                    inference_time = (time.perf_counter() - start_time) * 1000
                    self.total_inferences += 1
                    self.total_inference_time += inference_time
                    self.is_warm = True
                    # Remove internal _geo_emotion key before returning
                    mp_clean = {k: v for k, v in mp_data.items() if not k.startswith("_")}
                    return {
                        "success": True,
                        "emotion": fer_result["emotion"],
                        "confidence": fer_result["confidence"],
                        "all_probabilities": fer_result.get("all_probabilities", {}),
                        "box": fer_result.get("box"),
                        "inference_time_ms": round(inference_time, 2),
                        "source": "fer_library",
                        **mp_clean,
                    }

            # Fallback 2: Blendshape-based FER (MediaPipe Tasks FaceLandmarker)
            if self.blendshape_fer and self.blendshape_fer.is_available:
                bs_result = self.blendshape_fer.predict(image)
                if bs_result.get("success"):
                    inference_time = (time.perf_counter() - start_time) * 1000
                    self.total_inferences += 1
                    self.total_inference_time += inference_time
                    self.is_warm = True
                    # Remove internal _geo_emotion key before returning
                    mp_clean = {k: v for k, v in mp_data.items() if not k.startswith("_")}
                    return {
                        "success": True,
                        "emotion": bs_result["emotion"],
                        "confidence": bs_result["confidence"],
                        "all_probabilities": bs_result.get("all_probabilities", {}),
                        "inference_time_ms": round(inference_time, 2),
                        "source": "blendshape_fallback",
                        **mp_clean,
                    }

            # Fallback 2: Geometric emotion from MediaPipe Face Mesh landmarks
            geo_emotion = mp_data.pop("_geo_emotion", None)
            if geo_emotion and geo_emotion.get("emotion") != "neutral":
                inference_time = (time.perf_counter() - start_time) * 1000
                self.total_inferences += 1
                self.total_inference_time += inference_time
                self.is_warm = True
                return {
                    "success": True,
                    "emotion": geo_emotion["emotion"],
                    "confidence": geo_emotion["confidence"],
                    "all_probabilities": geo_emotion.get("all_probabilities", {}),
                    "inference_time_ms": round(inference_time, 2),
                    "source": geo_emotion.get("source", "geometric_landmarks"),
                    **mp_data,
                }

            # Fallback 3: Return geometric result even if neutral
            if geo_emotion:
                inference_time = (time.perf_counter() - start_time) * 1000
                self.total_inferences += 1
                self.total_inference_time += inference_time
                self.is_warm = True
                return {
                    "success": True,
                    "emotion": geo_emotion["emotion"],
                    "confidence": geo_emotion["confidence"],
                    "all_probabilities": geo_emotion.get("all_probabilities", {}),
                    "inference_time_ms": round(inference_time, 2),
                    "source": "geometric_landmarks",
                    **mp_data,
                }

            return {
                "success": False,
                "error": "Model not loaded",
                **mp_data,
            }

        # Clean internal keys before returning
        mp_clean = {k: v for k, v in mp_data.items() if not k.startswith("_")}

        try:
            # Preprocess
            input_tensor = self._preprocess_image(image).to(self.device)

            # Inference
            outputs = self.model(input_tensor)
            probabilities = F.softmax(outputs, dim=1).cpu().numpy()[0]

            # Get prediction
            predicted_idx = int(np.argmax(probabilities))
            confidence = float(probabilities[predicted_idx])

            # Build probability dict
            all_probs = {
                self.EMOTION_LABELS[i]: float(probabilities[i])
                for i in range(len(self.EMOTION_LABELS))
            }

            # Calculate inference time
            inference_time = (time.perf_counter() - start_time) * 1000  # ms

            # Update statistics
            self.total_inferences += 1
            self.total_inference_time += inference_time
            self.is_warm = True

            return {
                "success": True,
                "emotion": self.EMOTION_LABELS[predicted_idx],
                "confidence": confidence,
                "all_probabilities": all_probs,
                "inference_time_ms": round(inference_time, 2),
                **mp_clean,
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                **mp_clean,
            }

    def predict_from_base64(self, base64_string: str) -> Dict:
        """
        Run prediction from Base64 encoded image.

        Args:
            base64_string: Base64 encoded image

        Returns:
            Prediction results dictionary
        """
        try:
            image = self.decode_base64_frame(base64_string)
            return self.predict(image)
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to decode image: {str(e)}"
            }

    def get_status(self) -> Dict:
        """Get service status and statistics."""
        avg_time = (
            self.total_inference_time / self.total_inferences
            if self.total_inferences > 0 else 0.0
        )

        blendshape_available = (
            self.blendshape_fer is not None and self.blendshape_fer.is_available
        )

        fer_lib_available = (
            self.fer_library_service is not None and self.fer_library_service.is_available
        )

        return {
            "model_loaded": self.model is not None,
            "fer_library": fer_lib_available,
            "blendshape_fallback": blendshape_available,
            "fer_active": self.model is not None or fer_lib_available or blendshape_available,
            "device": str(self.device),
            "model_architecture": settings.fer_model_architecture,
            "warm": self.is_warm,
            "total_inferences": self.total_inferences,
            "avg_inference_time_ms": round(avg_time, 2)
        }

    def warmup(self) -> None:
        """Warm up the model with a dummy inference."""
        if self.model is None:
            return

        dummy_image = np.random.randint(0, 255, (224, 224, 3), dtype=np.uint8)
        self.predict(dummy_image)
        print("[INFERENCE] Model warmed up")


# Singleton accessor
_inference_service: Optional[InferenceService] = None


def get_inference_service() -> InferenceService:
    """Get the singleton inference service instance."""
    global _inference_service
    if _inference_service is None:
        _inference_service = InferenceService()
    return _inference_service
