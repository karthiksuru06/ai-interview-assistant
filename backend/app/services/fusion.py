"""
Multimodal Fusion Service
==========================
Combines video (FER) and audio emotion predictions for unified analysis.
Implements weighted fusion, mismatch detection, and real-time feedback.
"""

import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from collections import deque
from enum import Enum

import numpy as np


class ConfidenceLevel(Enum):
    """Confidence level classifications."""
    EXCELLENT = "excellent"
    GOOD = "good"
    MODERATE = "moderate"
    LOW = "low"
    CRITICAL = "critical"


@dataclass
class FusionResult:
    """Result of multimodal fusion."""
    # Primary outputs
    fused_emotion: str
    confidence_score: float
    confidence_level: ConfidenceLevel

    # Component scores
    video_emotion: str
    video_confidence: float
    audio_emotion: str
    audio_confidence: float

    # Analysis
    modality_agreement: bool
    nervous_cues_detected: bool
    nervous_cues: List[str]

    # Feedback
    feedback_tip: str
    detailed_feedback: List[str]

    # Metrics
    fusion_time_ms: float
    timestamp: float


@dataclass
class SessionState:
    """Tracks session state for temporal analysis."""
    emotion_history: deque = field(default_factory=lambda: deque(maxlen=30))
    confidence_history: deque = field(default_factory=lambda: deque(maxlen=30))
    mismatch_count: int = 0
    total_frames: int = 0
    nervous_cue_count: int = 0


class MultimodalFusionService:
    """
    Fuses video and audio emotion predictions.

    Fusion Strategy:
    - Weighted average: 60% video, 40% audio (visual cues more reliable)
    - Mismatch detection for nervous cues
    - Temporal smoothing for stability
    - Real-time feedback generation
    """

    EMOTION_LABELS = [
        "neutral", "happiness", "surprise", "sadness",
        "anger", "disgust", "fear", "contempt"
    ]

    # Emotion categories for mismatch detection
    POSITIVE_EMOTIONS = {"happiness", "surprise", "neutral"}
    NEGATIVE_EMOTIONS = {"sadness", "anger", "disgust", "fear", "contempt"}
    STRESS_INDICATORS = {"fear", "sadness", "disgust"}

    # Default fusion weights
    DEFAULT_VIDEO_WEIGHT = 0.6
    DEFAULT_AUDIO_WEIGHT = 0.4

    def __init__(
        self,
        video_weight: float = 0.6,
        audio_weight: float = 0.4,
        mismatch_threshold: float = 0.3,
        smoothing_window: int = 5
    ):
        """
        Initialize fusion service.

        Args:
            video_weight: Weight for video predictions (0-1)
            audio_weight: Weight for audio predictions (0-1)
            mismatch_threshold: Threshold for detecting modality mismatch
            smoothing_window: Window size for temporal smoothing
        """
        self.video_weight = video_weight
        self.audio_weight = audio_weight
        self.mismatch_threshold = mismatch_threshold
        self.smoothing_window = smoothing_window

        # Session states (keyed by session_id)
        self.sessions: Dict[str, SessionState] = {}

        # Feedback templates
        self._init_feedback_templates()

    def _init_feedback_templates(self) -> None:
        """Initialize feedback message templates."""
        self.feedback_templates = {
            "excellent_confidence": [
                "Excellent presence! You're projecting confidence.",
                "Great job! Your verbal and non-verbal cues align perfectly.",
                "Outstanding! Keep this energy throughout the interview."
            ],
            "good_confidence": [
                "Good composure. Stay relaxed and maintain eye contact.",
                "You're doing well. Remember to breathe steadily.",
                "Positive impression! Keep your answers structured."
            ],
            "moderate_confidence": [
                "Try to relax your facial muscles and speak clearly.",
                "Take a deep breath. You've got this!",
                "Focus on your strengths. Slow down if needed."
            ],
            "low_confidence": [
                "Pause and collect your thoughts. It's okay to take a moment.",
                "Try to maintain eye contact with the camera.",
                "Speak slowly and clearly. Your content matters most."
            ],
            "mismatch_detected": [
                "Your voice suggests nervousness - try to relax your shoulders.",
                "Mixed signals detected. Take a breath and reset.",
                "Your facial expression doesn't match your tone. Align them."
            ],
            "stress_detected": [
                "Signs of stress detected. Remember: it's just practice!",
                "You seem tense. Roll your shoulders and breathe deeply.",
                "Anxiety is normal. Channel it into enthusiasm!"
            ],
            "improvement": [
                "Your confidence is improving! Keep it up.",
                "Great progress from earlier. You're finding your rhythm.",
                "Nice recovery! You're adapting well."
            ]
        }

    def get_session(self, session_id: str) -> SessionState:
        """Get or create session state."""
        if session_id not in self.sessions:
            self.sessions[session_id] = SessionState()
        return self.sessions[session_id]

    def fuse(
        self,
        session_id: str,
        video_result: Optional[Dict] = None,
        audio_result: Optional[Dict] = None
    ) -> FusionResult:
        """
        Fuse video and audio predictions.

        Args:
            session_id: Session identifier
            video_result: Video inference result dict
            audio_result: Audio inference result dict

        Returns:
            FusionResult with combined analysis
        """
        start_time = time.perf_counter()
        session = self.get_session(session_id)
        session.total_frames += 1

        # Extract predictions
        video_emotion, video_conf, video_probs = self._extract_prediction(
            video_result, "video"
        )
        audio_emotion, audio_conf, audio_probs = self._extract_prediction(
            audio_result, "audio"
        )

        # Fuse probabilities
        fused_probs = self._fuse_probabilities(video_probs, audio_probs)
        fused_emotion = self.EMOTION_LABELS[np.argmax(fused_probs)]
        fused_confidence = float(np.max(fused_probs))

        # Calculate weighted confidence score
        confidence_score = self._calculate_confidence_score(
            video_conf, audio_conf, video_emotion, audio_emotion
        )

        # Detect modality agreement and nervous cues
        agreement, nervous_cues = self._analyze_modalities(
            video_emotion, video_conf,
            audio_emotion, audio_conf,
            session
        )

        # Determine confidence level
        confidence_level = self._get_confidence_level(confidence_score)

        # Generate feedback
        feedback_tip, detailed_feedback = self._generate_feedback(
            confidence_level, agreement, nervous_cues, session
        )

        # Update session history
        session.emotion_history.append(fused_emotion)
        session.confidence_history.append(confidence_score)

        fusion_time = (time.perf_counter() - start_time) * 1000

        return FusionResult(
            fused_emotion=fused_emotion,
            confidence_score=round(confidence_score, 2),
            confidence_level=confidence_level,
            video_emotion=video_emotion,
            video_confidence=round(video_conf, 3),
            audio_emotion=audio_emotion,
            audio_confidence=round(audio_conf, 3),
            modality_agreement=agreement,
            nervous_cues_detected=len(nervous_cues) > 0,
            nervous_cues=nervous_cues,
            feedback_tip=feedback_tip,
            detailed_feedback=detailed_feedback,
            fusion_time_ms=round(fusion_time, 2),
            timestamp=time.time()
        )

    def _extract_prediction(
        self,
        result: Optional[Dict],
        modality: str
    ) -> Tuple[str, float, np.ndarray]:
        """Extract emotion prediction from result dict."""
        if result is None or not result.get("success", False):
            # Return neutral with low confidence if modality unavailable
            probs = np.zeros(len(self.EMOTION_LABELS))
            probs[0] = 1.0  # neutral
            return "neutral", 0.3, probs

        emotion = result.get("emotion", "neutral")
        confidence = result.get("confidence", 0.5)

        # Get full probability distribution
        all_probs = result.get("all_probabilities", {})
        probs = np.array([
            all_probs.get(e, 0.0) for e in self.EMOTION_LABELS
        ])

        # Normalize if needed
        if probs.sum() > 0:
            probs = probs / probs.sum()
        else:
            probs = np.zeros(len(self.EMOTION_LABELS))
            probs[0] = 1.0

        return emotion, confidence, probs

    def _fuse_probabilities(
        self,
        video_probs: np.ndarray,
        audio_probs: np.ndarray
    ) -> np.ndarray:
        """Fuse probability distributions with weighted average."""
        fused = (
            self.video_weight * video_probs +
            self.audio_weight * audio_probs
        )
        return fused / fused.sum()

    def _calculate_confidence_score(
        self,
        video_conf: float,
        audio_conf: float,
        video_emotion: str,
        audio_emotion: str
    ) -> float:
        """
        Calculate unified confidence score.

        Formula: (0.6 * video_conf) + (0.4 * audio_conf) with agreement bonus
        """
        base_score = (
            self.video_weight * video_conf +
            self.audio_weight * audio_conf
        )

        # Agreement bonus (up to 10%)
        if video_emotion == audio_emotion:
            agreement_bonus = 0.1
        elif self._same_valence(video_emotion, audio_emotion):
            agreement_bonus = 0.05
        else:
            agreement_bonus = -0.05  # Penalty for mismatch

        # Positive emotion bonus (confidence indicators)
        if video_emotion in self.POSITIVE_EMOTIONS:
            emotion_bonus = 0.05
        elif video_emotion in self.STRESS_INDICATORS:
            emotion_bonus = -0.1
        else:
            emotion_bonus = 0

        final_score = base_score + agreement_bonus + emotion_bonus
        return max(0.0, min(1.0, final_score))

    def _same_valence(self, emotion1: str, emotion2: str) -> bool:
        """Check if two emotions have the same valence (positive/negative)."""
        in_positive = (
            emotion1 in self.POSITIVE_EMOTIONS and
            emotion2 in self.POSITIVE_EMOTIONS
        )
        in_negative = (
            emotion1 in self.NEGATIVE_EMOTIONS and
            emotion2 in self.NEGATIVE_EMOTIONS
        )
        return in_positive or in_negative

    def _analyze_modalities(
        self,
        video_emotion: str,
        video_conf: float,
        audio_emotion: str,
        audio_conf: float,
        session: SessionState
    ) -> Tuple[bool, List[str]]:
        """
        Analyze modality agreement and detect nervous cues.

        Returns:
            Tuple of (agreement_bool, list_of_nervous_cues)
        """
        nervous_cues = []

        # Check direct agreement
        agreement = video_emotion == audio_emotion

        # Check valence mismatch (more serious)
        valence_mismatch = (
            (video_emotion in self.POSITIVE_EMOTIONS and
             audio_emotion in self.NEGATIVE_EMOTIONS) or
            (video_emotion in self.NEGATIVE_EMOTIONS and
             audio_emotion in self.POSITIVE_EMOTIONS)
        )

        if valence_mismatch:
            session.mismatch_count += 1
            nervous_cues.append(
                f"Mixed signals: Face shows '{video_emotion}' but voice indicates '{audio_emotion}'"
            )

        # Detect specific nervous patterns
        if video_emotion == "happiness" and audio_emotion in self.STRESS_INDICATORS:
            nervous_cues.append("Nervous smile detected - voice betrays anxiety")
            session.nervous_cue_count += 1

        if audio_emotion == "fear" and video_conf > 0.7:
            nervous_cues.append("Voice tremor detected despite composed appearance")
            session.nervous_cue_count += 1

        if video_emotion == "neutral" and audio_emotion == "fear":
            nervous_cues.append("Masking behavior - trying to appear calm but voice shows stress")
            session.nervous_cue_count += 1

        # Check for sustained stress
        if len(session.emotion_history) >= 10:
            recent = list(session.emotion_history)[-10:]
            stress_count = sum(1 for e in recent if e in self.STRESS_INDICATORS)
            if stress_count >= 5:
                nervous_cues.append("Sustained stress detected - consider taking a break")

        # Check confidence drop
        if len(session.confidence_history) >= 5:
            recent_conf = list(session.confidence_history)[-5:]
            if recent_conf[-1] < recent_conf[0] - 0.2:
                nervous_cues.append("Confidence declining - reset and refocus")

        return agreement, nervous_cues

    def _get_confidence_level(self, score: float) -> ConfidenceLevel:
        """Convert confidence score to level."""
        if score >= 0.8:
            return ConfidenceLevel.EXCELLENT
        elif score >= 0.65:
            return ConfidenceLevel.GOOD
        elif score >= 0.5:
            return ConfidenceLevel.MODERATE
        elif score >= 0.35:
            return ConfidenceLevel.LOW
        else:
            return ConfidenceLevel.CRITICAL

    def _generate_feedback(
        self,
        level: ConfidenceLevel,
        agreement: bool,
        nervous_cues: List[str],
        session: SessionState
    ) -> Tuple[str, List[str]]:
        """Generate contextual feedback based on analysis."""
        import random

        detailed = []

        # Check for improvement
        if len(session.confidence_history) >= 10:
            recent = list(session.confidence_history)[-5:]
            earlier = list(session.confidence_history)[-10:-5]
            if np.mean(recent) > np.mean(earlier) + 0.1:
                tip = random.choice(self.feedback_templates["improvement"])
                detailed.append("Confidence trend: Improving ↑")
                return tip, detailed

        # Handle nervous cues first (priority)
        if nervous_cues:
            if any("Mixed signals" in cue for cue in nervous_cues):
                tip = random.choice(self.feedback_templates["mismatch_detected"])
            else:
                tip = random.choice(self.feedback_templates["stress_detected"])
            detailed.extend(nervous_cues)
            return tip, detailed

        # Generate based on confidence level
        level_key = f"{level.value}_confidence"
        if level_key in self.feedback_templates:
            tip = random.choice(self.feedback_templates[level_key])
        else:
            tip = random.choice(self.feedback_templates["moderate_confidence"])

        # Add detailed observations
        if level in [ConfidenceLevel.EXCELLENT, ConfidenceLevel.GOOD]:
            detailed.append("Verbal and non-verbal cues are aligned")
            if agreement:
                detailed.append("Consistent emotional expression across modalities")
        else:
            detailed.append("Room for improvement in presentation confidence")
            if not agreement:
                detailed.append("Work on aligning facial expressions with voice tone")

        return tip, detailed

    def get_session_summary(self, session_id: str) -> Dict:
        """Get summary statistics for a session."""
        session = self.sessions.get(session_id)

        if session is None or session.total_frames == 0:
            return {"error": "No session data"}

        confidence_list = list(session.confidence_history)
        emotion_list = list(session.emotion_history)

        # Calculate statistics
        avg_confidence = np.mean(confidence_list) if confidence_list else 0
        confidence_std = np.std(confidence_list) if confidence_list else 0

        # Emotion distribution
        emotion_counts = {}
        for e in emotion_list:
            emotion_counts[e] = emotion_counts.get(e, 0) + 1

        dominant_emotion = max(emotion_counts, key=emotion_counts.get) if emotion_counts else "neutral"

        # Mismatch rate
        mismatch_rate = session.mismatch_count / max(1, session.total_frames)

        return {
            "session_id": session_id,
            "total_frames": session.total_frames,
            "avg_confidence": round(avg_confidence, 3),
            "confidence_stability": round(1 - confidence_std, 3),
            "dominant_emotion": dominant_emotion,
            "emotion_distribution": emotion_counts,
            "mismatch_rate": round(mismatch_rate, 3),
            "nervous_cue_count": session.nervous_cue_count,
            "overall_rating": self._calculate_rating(avg_confidence, mismatch_rate)
        }

    def _calculate_rating(self, avg_conf: float, mismatch_rate: float) -> str:
        """Calculate overall session rating."""
        score = avg_conf - (mismatch_rate * 0.2)

        if score >= 0.75:
            return "Excellent - Interview Ready"
        elif score >= 0.6:
            return "Good - Minor improvements needed"
        elif score >= 0.45:
            return "Average - Practice recommended"
        else:
            return "Needs Work - Focus on fundamentals"

    def clear_session(self, session_id: str) -> None:
        """Clear session data."""
        self.sessions.pop(session_id, None)


# Singleton instance
_fusion_service: Optional[MultimodalFusionService] = None


def get_fusion_service() -> MultimodalFusionService:
    """Get singleton fusion service."""
    global _fusion_service
    if _fusion_service is None:
        _fusion_service = MultimodalFusionService()
    return _fusion_service
