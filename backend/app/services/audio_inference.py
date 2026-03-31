"""
Audio Emotion Inference Service
================================
Real-time voice emotion recognition from raw audio.
Extracts MFCC features on-the-fly and runs LSTM inference.

Optimized for low-latency on NVIDIA RTX 4060.
"""

import io
import time
import threading
from typing import Dict, List, Optional, Tuple
from collections import deque
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

from app.config import settings


# ============================================================================
# MFCC Feature Extractor
# ============================================================================

class MFCCExtractor:
    """
    Extract MFCC features from raw audio.

    Uses torchaudio for GPU-accelerated extraction when available,
    falls back to librosa for CPU.
    """

    def __init__(
        self,
        sample_rate: int = 16000,
        n_mfcc: int = 40,
        n_fft: int = 512,
        hop_length: int = 160,  # 10ms at 16kHz
        n_mels: int = 80,
        use_gpu: bool = True
    ):
        """
        Initialize MFCC extractor.

        Args:
            sample_rate: Audio sample rate
            n_mfcc: Number of MFCC coefficients
            n_fft: FFT window size
            hop_length: Hop length between frames
            n_mels: Number of mel filterbanks
            use_gpu: Use GPU for extraction if available
        """
        self.sample_rate = sample_rate
        self.n_mfcc = n_mfcc
        self.n_fft = n_fft
        self.hop_length = hop_length
        self.n_mels = n_mels

        self.device = torch.device("cpu")
        self.use_torchaudio = False

        # Try to use torchaudio (faster)
        try:
            import torchaudio
            import torchaudio.transforms as T

            if use_gpu and torch.cuda.is_available():
                self.device = torch.device("cuda")

            self.mfcc_transform = T.MFCC(
                sample_rate=sample_rate,
                n_mfcc=n_mfcc,
                melkwargs={
                    "n_fft": n_fft,
                    "hop_length": hop_length,
                    "n_mels": n_mels,
                    "center": True,
                    "pad_mode": "reflect",
                    "norm": "slaney",
                    "mel_scale": "htk"
                }
            ).to(self.device)

            self.use_torchaudio = True
            print(f"[MFCC] Using torchaudio on {self.device}")

        except ImportError:
            print("[MFCC] torchaudio not available, using librosa")
            import librosa
            self.librosa = librosa

    def extract(self, audio: np.ndarray) -> np.ndarray:
        """
        Extract MFCC features from audio.

        Args:
            audio: Audio samples (float32, mono, normalized to [-1, 1])

        Returns:
            MFCC features [Time, n_mfcc]
        """
        if self.use_torchaudio:
            return self._extract_torchaudio(audio)
        else:
            return self._extract_librosa(audio)

    def _extract_torchaudio(self, audio: np.ndarray) -> np.ndarray:
        """Extract using torchaudio (GPU-accelerated)."""
        # Convert to tensor
        waveform = torch.tensor(audio, dtype=torch.float32).unsqueeze(0)
        waveform = waveform.to(self.device)

        # Extract MFCC [1, n_mfcc, Time]
        mfcc = self.mfcc_transform(waveform)

        # Transpose to [Time, n_mfcc] and move to CPU
        mfcc = mfcc.squeeze(0).transpose(0, 1).cpu().numpy()

        return mfcc

    def _extract_librosa(self, audio: np.ndarray) -> np.ndarray:
        """Extract using librosa (CPU)."""
        mfcc = self.librosa.feature.mfcc(
            y=audio,
            sr=self.sample_rate,
            n_mfcc=self.n_mfcc,
            n_fft=self.n_fft,
            hop_length=self.hop_length,
            n_mels=self.n_mels
        )

        # Transpose to [Time, n_mfcc]
        return mfcc.T


# ============================================================================
# Audio LSTM Model (Inference Version)
# ============================================================================

class AudioLSTMInference(nn.Module):
    """
    Lightweight LSTM model for inference.
    Matches the training architecture but optimized for single-sample inference.
    """

    def __init__(
        self,
        input_size: int = 40,
        hidden_size: int = 128,
        num_layers: int = 2,
        num_classes: int = 8,
        dropout: float = 0.0,  # Disabled for inference
        bidirectional: bool = True
    ):
        super().__init__()

        self.hidden_size = hidden_size
        self.num_layers = num_layers
        self.num_directions = 2 if bidirectional else 1

        self.input_norm = nn.LayerNorm(input_size)

        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
            dropout=0,
            bidirectional=bidirectional
        )

        lstm_output_size = hidden_size * self.num_directions

        self.attention = nn.Sequential(
            nn.Linear(lstm_output_size, hidden_size),
            nn.Tanh(),
            nn.Linear(hidden_size, 1, bias=False)
        )

        self.fc = nn.Sequential(
            nn.Linear(lstm_output_size, hidden_size),
            nn.ReLU(inplace=True),
            nn.Linear(hidden_size, num_classes)
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.input_norm(x)
        lstm_out, _ = self.lstm(x)

        # Attention pooling
        attn_scores = self.attention(lstm_out).squeeze(-1)
        attn_weights = F.softmax(attn_scores, dim=1).unsqueeze(-1)
        context = torch.sum(lstm_out * attn_weights, dim=1)

        logits = self.fc(context)
        return logits


# ============================================================================
# Inference Service
# ============================================================================

class AudioInferenceService:
    """
    Real-time audio emotion inference service.

    Takes raw audio bytes, extracts MFCCs, and predicts emotion.
    Optimized for low-latency inference on RTX 4060.
    """

    EMOTION_LABELS = [
        "neutral", "happiness", "surprise", "sadness",
        "anger", "disgust", "fear", "contempt"
    ]

    _instance: Optional["AudioInferenceService"] = None
    _lock = threading.Lock()

    def __new__(cls) -> "AudioInferenceService":
        """Singleton pattern."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(
        self,
        model_path: Optional[str] = None,
        sample_rate: int = 16000,
        n_mfcc: int = 40
    ):
        """
        Initialize audio inference service.

        Args:
            model_path: Path to trained model checkpoint
            sample_rate: Expected audio sample rate
            n_mfcc: Number of MFCC coefficients
        """
        if self._initialized:
            return

        self._initialized = True

        self.sample_rate = sample_rate
        self.n_mfcc = n_mfcc
        self.model: Optional[nn.Module] = None
        self.device = torch.device("cpu")

        # Statistics
        self.total_inferences = 0
        self.total_inference_time = 0.0
        self.is_warm = False

        # Initialize components
        self._setup_device()
        self.mfcc_extractor = MFCCExtractor(
            sample_rate=sample_rate,
            n_mfcc=n_mfcc,
            use_gpu=(self.device.type == "cuda")
        )

        # Emotion history for smoothing
        self.emotion_history: deque = deque(maxlen=5)

    def _setup_device(self) -> None:
        """Configure compute device."""
        if torch.cuda.is_available():
            self.device = torch.device("cuda")
            gpu_name = torch.cuda.get_device_name(0)
            print(f"[AUDIO INFERENCE] GPU: {gpu_name}")
            torch.backends.cudnn.benchmark = True
        else:
            self.device = torch.device("cpu")
            print("[AUDIO INFERENCE] Running on CPU")

    def load_model(self, model_path: Optional[str] = None) -> bool:
        """
        Load trained audio model.

        Args:
            model_path: Path to checkpoint file

        Returns:
            True if loaded successfully
        """
        path = model_path or getattr(settings, 'audio_model_path', './checkpoints/audio_best.pth')

        try:
            print(f"[AUDIO INFERENCE] Loading model from: {path}")

            checkpoint = torch.load(path, map_location=self.device)

            # Get config from checkpoint
            config = checkpoint.get("config", {})
            input_size = config.get("input_size", 40)
            hidden_size = config.get("hidden_size", 128)
            num_classes = config.get("num_classes", 8)

            # Create model
            self.model = AudioLSTMInference(
                input_size=input_size,
                hidden_size=hidden_size,
                num_layers=2,
                num_classes=num_classes,
                bidirectional=True
            )

            # Load weights
            self.model.load_state_dict(checkpoint["model_state_dict"])
            self.model = self.model.to(self.device)
            self.model.eval()

            # Enable inference optimizations
            if self.device.type == "cuda":
                self.model = torch.jit.script(self.model)

            print(f"[AUDIO INFERENCE] Model loaded (epoch {checkpoint.get('epoch', '?')})")
            print(f"[AUDIO INFERENCE] Val accuracy: {checkpoint.get('val_acc', 0):.4f}")

            return True

        except FileNotFoundError:
            print(f"[AUDIO INFERENCE] Model not found: {path}")
            return False
        except Exception as e:
            print(f"[AUDIO INFERENCE] Error loading model: {e}")
            return False

    def preprocess_audio(self, audio_bytes: bytes) -> np.ndarray:
        """
        Convert raw audio bytes to float32 array.

        Args:
            audio_bytes: Raw audio bytes (PCM int16 or float32)

        Returns:
            Normalized audio array [-1, 1]
        """
        # Try to detect format
        audio = np.frombuffer(audio_bytes, dtype=np.int16)
        audio = audio.astype(np.float32) / 32768.0

        return audio

    def extract_features(self, audio: np.ndarray) -> torch.Tensor:
        """
        Extract MFCC features from audio.

        Args:
            audio: Audio samples

        Returns:
            MFCC tensor [1, Time, n_mfcc]
        """
        # Extract MFCCs
        mfcc = self.mfcc_extractor.extract(audio)

        # Convert to tensor and add batch dimension
        mfcc_tensor = torch.tensor(mfcc, dtype=torch.float32).unsqueeze(0)

        return mfcc_tensor.to(self.device)

    @torch.no_grad()
    def predict(self, audio: np.ndarray) -> Dict:
        """
        Predict emotion from audio samples.

        Args:
            audio: Audio samples (float32, mono)

        Returns:
            Prediction results dictionary
        """
        if self.model is None:
            return {
                "success": False,
                "error": "Model not loaded"
            }

        start_time = time.perf_counter()

        try:
            # Extract features
            features = self.extract_features(audio)

            # Check minimum length
            if features.size(1) < 10:
                return {
                    "success": False,
                    "error": "Audio too short"
                }

            # Inference
            outputs = self.model(features)
            probabilities = F.softmax(outputs, dim=-1).cpu().numpy()[0]

            # Get prediction
            predicted_idx = int(np.argmax(probabilities))
            confidence = float(probabilities[predicted_idx])

            # Build probability dict
            all_probs = {
                self.EMOTION_LABELS[i]: float(probabilities[i])
                for i in range(len(self.EMOTION_LABELS))
            }

            # Apply temporal smoothing
            self.emotion_history.append(probabilities)
            if len(self.emotion_history) >= 3:
                smoothed_probs = np.mean(list(self.emotion_history), axis=0)
                smoothed_idx = int(np.argmax(smoothed_probs))
                smoothed_confidence = float(smoothed_probs[smoothed_idx])
                smoothed_emotion = self.EMOTION_LABELS[smoothed_idx]
            else:
                smoothed_emotion = self.EMOTION_LABELS[predicted_idx]
                smoothed_confidence = confidence

            # Calculate inference time
            inference_time = (time.perf_counter() - start_time) * 1000

            # Update statistics
            self.total_inferences += 1
            self.total_inference_time += inference_time
            self.is_warm = True

            return {
                "success": True,
                "emotion": self.EMOTION_LABELS[predicted_idx],
                "confidence": confidence,
                "smoothed_emotion": smoothed_emotion,
                "smoothed_confidence": smoothed_confidence,
                "all_probabilities": all_probs,
                "inference_time_ms": round(inference_time, 2)
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def predict_from_bytes(self, audio_bytes: bytes) -> Dict:
        """
        Predict emotion from raw audio bytes.

        Args:
            audio_bytes: Raw PCM audio bytes

        Returns:
            Prediction results
        """
        try:
            audio = self.preprocess_audio(audio_bytes)
            return self.predict(audio)
        except Exception as e:
            return {
                "success": False,
                "error": f"Audio preprocessing failed: {str(e)}"
            }

    def predict_from_base64(self, base64_string: str) -> Dict:
        """
        Predict from base64 encoded audio.

        Args:
            base64_string: Base64 encoded audio

        Returns:
            Prediction results
        """
        import base64

        try:
            if "base64," in base64_string:
                base64_string = base64_string.split("base64,")[1]

            audio_bytes = base64.b64decode(base64_string)
            return self.predict_from_bytes(audio_bytes)
        except Exception as e:
            return {
                "success": False,
                "error": f"Base64 decode failed: {str(e)}"
            }

    def warmup(self) -> None:
        """Warm up the model with dummy inference."""
        if self.model is None:
            return

        dummy_audio = np.random.randn(16000).astype(np.float32) * 0.1
        self.predict(dummy_audio)
        self.emotion_history.clear()
        print("[AUDIO INFERENCE] Model warmed up")

    def get_status(self) -> Dict:
        """Get service status."""
        avg_time = (
            self.total_inference_time / self.total_inferences
            if self.total_inferences > 0 else 0
        )

        return {
            "model_loaded": self.model is not None,
            "device": str(self.device),
            "sample_rate": self.sample_rate,
            "n_mfcc": self.n_mfcc,
            "warm": self.is_warm,
            "total_inferences": self.total_inferences,
            "avg_inference_time_ms": round(avg_time, 2)
        }

    def reset_history(self) -> None:
        """Reset emotion history (for new session)."""
        self.emotion_history.clear()


# Singleton accessor
_audio_inference_service: Optional[AudioInferenceService] = None


def get_audio_inference_service() -> AudioInferenceService:
    """Get the singleton audio inference service."""
    global _audio_inference_service
    if _audio_inference_service is None:
        _audio_inference_service = AudioInferenceService()
    return _audio_inference_service


# ============================================================================
# Testing
# ============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Testing Audio Inference Service")
    print("=" * 60)

    service = get_audio_inference_service()

    # Try to load model
    model_loaded = service.load_model()

    if model_loaded:
        service.warmup()

        # Test with random audio
        print("\nTesting inference...")
        dummy_audio = np.random.randn(16000).astype(np.float32) * 0.1

        result = service.predict(dummy_audio)
        print(f"Result: {result}")

        print(f"\nService status: {service.get_status()}")
    else:
        print("\nModel not found - testing MFCC extraction only...")

        extractor = MFCCExtractor(sample_rate=16000, n_mfcc=40)
        dummy_audio = np.random.randn(16000).astype(np.float32) * 0.1

        start = time.perf_counter()
        mfcc = extractor.extract(dummy_audio)
        elapsed = (time.perf_counter() - start) * 1000

        print(f"MFCC shape: {mfcc.shape}")
        print(f"Extraction time: {elapsed:.2f}ms")

    print("\n[SUCCESS] Test complete!")
