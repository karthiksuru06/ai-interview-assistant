"""
Metrics Calculator Service
==========================
Unified service for calculating the 5 core interview metrics
and the combined Interview Readiness Score (IRS).
"""

from collections import deque
from typing import Dict, List, Optional
from dataclasses import dataclass, field
import time


@dataclass
class MetricSnapshot:
    """Point-in-time metric values."""
    timestamp: float
    facial_confidence: float = 0.0
    eye_contact: float = 0.0
    voice_clarity: float = 0.0
    emotional_stability: float = 0.0
    fluency: float = 0.0
    irs: float = 0.0


@dataclass
class SessionMetrics:
    """Aggregated metrics for an interview session."""
    session_id: str
    total_frames: int = 0
    total_audio_chunks: int = 0

    # Running averages
    avg_facial_confidence: float = 0.0
    avg_eye_contact: float = 0.0
    avg_voice_clarity: float = 0.0
    avg_emotional_stability: float = 0.0
    avg_fluency: float = 0.0
    avg_irs: float = 0.0

    # History for trends
    metric_history: List[MetricSnapshot] = field(default_factory=list)

    # Emotion tracking
    emotion_counts: Dict[str, int] = field(default_factory=dict)
    dominant_emotion: str = "neutral"


class MetricsCalculator:
    """
    Calculate and track the 5 core interview metrics.

    Metrics:
    1. Facial Confidence (FCS): Based on FER emotion analysis
    2. Eye Contact (ECS): Based on gaze tracking
    3. Voice Clarity (VCS): Based on audio analysis
    4. Emotional Stability (ESS): Based on emotion variance
    5. Fluency (FS): Based on speech analysis

    Combined: Interview Readiness Score (IRS)
    """

    # Emotion weights for facial confidence calculation
    EMOTION_WEIGHTS = {
        'happiness': 1.0,
        'neutral': 0.7,
        'surprise': 0.3,
        'fear': -0.8,
        'sadness': -0.5,
        'anger': -0.3,
        'disgust': -0.4,
        'contempt': -0.2
    }

    # IRS component weights
    DEFAULT_IRS_WEIGHTS = {
        'facial_confidence': 0.20,
        'eye_contact': 0.15,
        'voice_clarity': 0.20,
        'emotional_stability': 0.25,
        'fluency': 0.20
    }

    def __init__(self, session_id: str, smoothing_factor: float = 0.3):
        """
        Initialize metrics calculator for a session.

        Args:
            session_id: Unique session identifier
            smoothing_factor: EMA alpha for temporal smoothing (0-1)
        """
        self.session_id = session_id
        self.alpha = smoothing_factor

        # Initialize session metrics
        self.metrics = SessionMetrics(session_id=session_id)

        # History for smoothing
        self.facial_history: deque = deque(maxlen=30)
        self.eye_contact_history: deque = deque(maxlen=30)
        self.clarity_history: deque = deque(maxlen=10)
        self.fluency_history: deque = deque(maxlen=10)

        # Current smoothed values
        self._current = MetricSnapshot(timestamp=time.time())

    def calculate_facial_confidence(
        self,
        emotion_probs: Dict[str, float]
    ) -> float:
        """
        Calculate facial confidence score from emotion probabilities.

        Args:
            emotion_probs: Dict of emotion -> probability

        Returns:
            Facial confidence score (0-100)
        """
        # Weighted sum of emotion probabilities
        raw_score = sum(
            emotion_probs.get(emotion, 0) * weight
            for emotion, weight in self.EMOTION_WEIGHTS.items()
        )

        # Normalize: raw range [-0.8, 1.0] -> [0, 100]
        normalized = ((raw_score + 0.8) / 1.8) * 100

        # Apply temporal smoothing (EMA)
        self.facial_history.append(normalized)
        if len(self.facial_history) > 1:
            smoothed = (
                self.alpha * normalized +
                (1 - self.alpha) * self._current.facial_confidence
            )
        else:
            smoothed = normalized

        smoothed = max(0, min(100, smoothed))
        self._current.facial_confidence = smoothed

        # Update emotion counts
        if emotion_probs:
            dominant = max(emotion_probs, key=emotion_probs.get)
            self.metrics.emotion_counts[dominant] = (
                self.metrics.emotion_counts.get(dominant, 0) + 1
            )

        return smoothed

    def calculate_eye_contact(
        self,
        gaze_deviation: float,
        is_looking_at_camera: bool
    ) -> float:
        """
        Calculate eye contact score from gaze data.

        Args:
            gaze_deviation: Distance from center (0-1, 0 = perfect)
            is_looking_at_camera: Boolean flag

        Returns:
            Eye contact score (0-100)
        """
        MAX_DEVIATION = 0.7

        # Base score from deviation
        raw_score = max(0, (1 - gaze_deviation / MAX_DEVIATION)) * 100

        # Bonus for direct eye contact
        if is_looking_at_camera:
            raw_score = min(100, raw_score + 10)

        # Temporal smoothing
        self.eye_contact_history.append(raw_score)
        if len(self.eye_contact_history) > 1:
            smoothed = (
                self.alpha * raw_score +
                (1 - self.alpha) * self._current.eye_contact
            )
        else:
            smoothed = raw_score

        # Also factor in stability (consistency of eye contact)
        if len(self.eye_contact_history) >= 10:
            recent = list(self.eye_contact_history)[-10:]
            variance = sum((x - sum(recent)/len(recent))**2 for x in recent) / len(recent)
            stability = max(0, (1 - (variance ** 0.5) / 30)) * 100
            smoothed = 0.7 * smoothed + 0.3 * stability

        smoothed = max(0, min(100, smoothed))
        self._current.eye_contact = smoothed

        return smoothed

    def update_voice_clarity(self, clarity_score: float) -> float:
        """
        Update voice clarity metric.

        Args:
            clarity_score: Voice clarity score from audio analyzer

        Returns:
            Smoothed clarity score (0-100)
        """
        self.clarity_history.append(clarity_score)

        if len(self.clarity_history) > 1:
            smoothed = (
                self.alpha * clarity_score +
                (1 - self.alpha) * self._current.voice_clarity
            )
        else:
            smoothed = clarity_score

        smoothed = max(0, min(100, smoothed))
        self._current.voice_clarity = smoothed

        return smoothed

    def update_emotional_stability(self, stability_score: float) -> float:
        """
        Update emotional stability metric.

        Args:
            stability_score: Stability score from stability tracker

        Returns:
            Current stability score (0-100)
        """
        self._current.emotional_stability = max(0, min(100, stability_score))
        return self._current.emotional_stability

    def update_fluency(self, fluency_score: float) -> float:
        """
        Update fluency metric.

        Args:
            fluency_score: Fluency score from fluency analyzer

        Returns:
            Smoothed fluency score (0-100)
        """
        self.fluency_history.append(fluency_score)

        if len(self.fluency_history) > 1:
            smoothed = (
                self.alpha * fluency_score +
                (1 - self.alpha) * self._current.fluency
            )
        else:
            smoothed = fluency_score

        smoothed = max(0, min(100, smoothed))
        self._current.fluency = smoothed

        return smoothed

    def calculate_irs(
        self,
        weights: Optional[Dict[str, float]] = None
    ) -> Dict:
        """
        Calculate Interview Readiness Score.

        Args:
            weights: Optional custom weights for components

        Returns:
            IRS result with breakdown
        """
        weights = weights or self.DEFAULT_IRS_WEIGHTS

        scores = {
            'facial_confidence': self._current.facial_confidence,
            'eye_contact': self._current.eye_contact,
            'voice_clarity': self._current.voice_clarity,
            'emotional_stability': self._current.emotional_stability,
            'fluency': self._current.fluency
        }

        # Weighted average
        irs = sum(scores[k] * weights[k] for k in scores)
        self._current.irs = irs

        # Determine rating
        if irs >= 80:
            rating = "Interview Ready"
            color = "green"
        elif irs >= 60:
            rating = "Good Progress"
            color = "blue"
        elif irs >= 40:
            rating = "Needs Practice"
            color = "yellow"
        else:
            rating = "Focus on Fundamentals"
            color = "red"

        # Identify strengths and weaknesses
        sorted_scores = sorted(scores.items(), key=lambda x: x[1])
        weakest = sorted_scores[0][0]
        strongest = sorted_scores[-1][0]

        return {
            'irs': round(irs, 1),
            'rating': rating,
            'color': color,
            'component_scores': {k: round(v, 1) for k, v in scores.items()},
            'weights': weights,
            'strongest_area': strongest,
            'weakest_area': weakest,
            'priority_improvement': weakest
        }

    def process_video_frame(
        self,
        emotion_probs: Dict[str, float],
        gaze_deviation: float = 0.0,
        is_looking_at_camera: bool = True
    ) -> Dict:
        """
        Process a video frame and update all visual metrics.

        Args:
            emotion_probs: Emotion probabilities from FER
            gaze_deviation: Gaze deviation from gaze tracker
            is_looking_at_camera: Eye contact flag

        Returns:
            Updated metrics dictionary
        """
        self.metrics.total_frames += 1

        facial = self.calculate_facial_confidence(emotion_probs)
        eye = self.calculate_eye_contact(gaze_deviation, is_looking_at_camera)

        # Get IRS (may use stale audio metrics)
        irs_result = self.calculate_irs()

        return {
            'facial_confidence': round(facial, 1),
            'eye_contact': round(eye, 1),
            'emotional_stability': round(self._current.emotional_stability, 1),
            'voice_clarity': round(self._current.voice_clarity, 1),
            'fluency': round(self._current.fluency, 1),
            'irs': irs_result['irs'],
            'rating': irs_result['rating']
        }

    def process_audio_chunk(
        self,
        clarity_score: float,
        fluency_score: float,
        stability_score: Optional[float] = None
    ) -> Dict:
        """
        Process an audio chunk and update audio metrics.

        Args:
            clarity_score: Voice clarity score
            fluency_score: Speech fluency score
            stability_score: Optional emotional stability update

        Returns:
            Updated metrics dictionary
        """
        self.metrics.total_audio_chunks += 1

        clarity = self.update_voice_clarity(clarity_score)
        fluency = self.update_fluency(fluency_score)

        if stability_score is not None:
            self.update_emotional_stability(stability_score)

        irs_result = self.calculate_irs()

        return {
            'voice_clarity': round(clarity, 1),
            'fluency': round(fluency, 1),
            'emotional_stability': round(self._current.emotional_stability, 1),
            'irs': irs_result['irs'],
            'rating': irs_result['rating']
        }

    def get_current_metrics(self) -> Dict:
        """Get current metric values."""
        irs_result = self.calculate_irs()

        return {
            'timestamp': time.time(),
            'session_id': self.session_id,
            'metrics': {
                'facial_confidence': round(self._current.facial_confidence, 1),
                'eye_contact': round(self._current.eye_contact, 1),
                'voice_clarity': round(self._current.voice_clarity, 1),
                'emotional_stability': round(self._current.emotional_stability, 1),
                'fluency': round(self._current.fluency, 1)
            },
            'irs': irs_result,
            'statistics': {
                'total_frames': self.metrics.total_frames,
                'total_audio_chunks': self.metrics.total_audio_chunks,
                'dominant_emotion': self._get_dominant_emotion()
            }
        }

    def _get_dominant_emotion(self) -> str:
        """Get the most frequent emotion in the session."""
        if not self.metrics.emotion_counts:
            return "neutral"
        return max(self.metrics.emotion_counts, key=self.metrics.emotion_counts.get)

    def get_session_summary(self) -> Dict:
        """Get complete session summary."""
        total_emotions = sum(self.metrics.emotion_counts.values())
        emotion_distribution = {
            k: round(v / max(1, total_emotions), 3)
            for k, v in self.metrics.emotion_counts.items()
        }

        return {
            'session_id': self.session_id,
            'total_frames_analyzed': self.metrics.total_frames,
            'total_audio_chunks': self.metrics.total_audio_chunks,
            'final_metrics': {
                'facial_confidence': round(self._current.facial_confidence, 1),
                'eye_contact': round(self._current.eye_contact, 1),
                'voice_clarity': round(self._current.voice_clarity, 1),
                'emotional_stability': round(self._current.emotional_stability, 1),
                'fluency': round(self._current.fluency, 1)
            },
            'final_irs': self.calculate_irs(),
            'emotion_distribution': emotion_distribution,
            'dominant_emotion': self._get_dominant_emotion()
        }


# Session-based calculator storage
_calculators: Dict[str, MetricsCalculator] = {}


def get_metrics_calculator(session_id: str) -> MetricsCalculator:
    """Get or create a metrics calculator for a session."""
    if session_id not in _calculators:
        _calculators[session_id] = MetricsCalculator(session_id)
    return _calculators[session_id]


def remove_metrics_calculator(session_id: str) -> None:
    """Remove a calculator when session ends."""
    _calculators.pop(session_id, None)
