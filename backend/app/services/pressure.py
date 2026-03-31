"""
Pressure Manager Service
========================
Manages dynamic interview pressure/difficulty based on candidate's
emotional state (50%) and performance metrics (50%).
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum
import time


class DifficultyLevel(str, Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class PressureZone(str, Enum):
    COMFORT = "comfort"      # 0-30: Low pressure, easy questions
    GROWTH = "growth"        # 30-70: Optimal learning zone
    CHALLENGE = "challenge"  # 70-100: High pressure, hard questions


@dataclass
class PressureState:
    """Current pressure state snapshot."""
    pressure_level: float  # 0-100
    difficulty: DifficultyLevel
    zone: PressureZone
    emotion_component: float  # 0-50
    performance_component: float  # 0-50
    feedback: str
    tips: List[str]
    timestamp: float = field(default_factory=time.time)


# Emotion categories and their pressure impact
NEGATIVE_EMOTIONS = {"fear", "sadness", "anger", "disgust", "contempt"}
POSITIVE_EMOTIONS = {"happiness", "surprise"}
NEUTRAL_EMOTIONS = {"neutral"}

# Stress indicator emotions
STRESS_INDICATORS = {"fear", "sadness", "disgust"}


class PressureManager:
    """
    Manages interview pressure/difficulty dynamically.

    Pressure is calculated from two components:
    - Emotion Factor (50%): Based on detected emotional state
    - Performance Factor (50%): Based on answer scores and response times

    Pressure ranges:
    - 0-30: Comfort zone (easy difficulty)
    - 30-70: Growth zone (medium difficulty)
    - 70-100: Challenge zone (hard difficulty)
    """

    # Difficulty mapping based on pressure level
    DIFFICULTY_RANGES: Dict[Tuple[int, int], DifficultyLevel] = {
        (0, 30): DifficultyLevel.EASY,
        (30, 70): DifficultyLevel.MEDIUM,
        (70, 101): DifficultyLevel.HARD,
    }

    # Pressure zone mapping
    ZONE_RANGES: Dict[Tuple[int, int], PressureZone] = {
        (0, 30): PressureZone.COMFORT,
        (30, 70): PressureZone.GROWTH,
        (70, 101): PressureZone.CHALLENGE,
    }

    def __init__(
        self,
        base_difficulty: str = "medium",
        emotion_weight: float = 0.5,
        performance_weight: float = 0.5
    ):
        """
        Initialize pressure manager.

        Args:
            base_difficulty: Starting difficulty level
            emotion_weight: Weight for emotion component (default 0.5)
            performance_weight: Weight for performance component (default 0.5)
        """
        self.base_difficulty = DifficultyLevel(base_difficulty.lower())
        self.emotion_weight = emotion_weight
        self.performance_weight = performance_weight

        # Set initial pressure based on base difficulty
        self._init_pressure_from_difficulty()

        # Tracking state
        self.emotion_history: List[Dict] = []
        self.answer_scores: List[float] = []
        self.response_times: List[float] = []

        # Smoothing factor for gradual changes
        self.smoothing_factor = 0.3  # Lower = more gradual changes

        # Consecutive tracking for adaptive adjustments
        self.consecutive_negative_emotions = 0
        self.consecutive_positive_emotions = 0
        self.consecutive_low_scores = 0
        self.consecutive_high_scores = 0

    def _init_pressure_from_difficulty(self):
        """Initialize pressure level based on starting difficulty."""
        difficulty_to_pressure = {
            DifficultyLevel.EASY: 20,
            DifficultyLevel.MEDIUM: 50,
            DifficultyLevel.HARD: 80,
        }
        self.pressure_level = difficulty_to_pressure.get(self.base_difficulty, 50)
        self.emotion_component = self.pressure_level * self.emotion_weight
        self.performance_component = self.pressure_level * self.performance_weight

    def update_emotion(self, emotion: str, confidence: float = 1.0) -> None:
        """
        Update pressure based on detected emotion.

        Args:
            emotion: Detected emotion string
            confidence: Confidence score (0-1)
        """
        emotion = emotion.lower()

        # Record emotion
        self.emotion_history.append({
            "emotion": emotion,
            "confidence": confidence,
            "timestamp": time.time()
        })

        # Keep only last 20 emotions for recent context
        self.emotion_history = self.emotion_history[-20:]

        # Calculate emotion pressure adjustment
        adjustment = 0

        if emotion in NEGATIVE_EMOTIONS:
            self.consecutive_negative_emotions += 1
            self.consecutive_positive_emotions = 0

            # Base adjustment for negative emotions
            base_adjustment = 2 * confidence

            # Extra adjustment for stress indicators
            if emotion in STRESS_INDICATORS:
                base_adjustment += 1.5 * confidence

            # Consecutive negative emotions increase pressure faster
            if self.consecutive_negative_emotions > 3:
                base_adjustment *= 1.5

            adjustment = base_adjustment

        elif emotion in POSITIVE_EMOTIONS:
            self.consecutive_positive_emotions += 1
            self.consecutive_negative_emotions = 0

            # Positive emotions reduce pressure
            adjustment = -1.5 * confidence

            # Consecutive positive emotions reduce pressure faster
            if self.consecutive_positive_emotions > 3:
                adjustment *= 1.3

        else:  # Neutral
            # Neutral maintains stability, slight pressure reduction
            adjustment = -0.5 * confidence
            # Reset consecutive counters gradually
            self.consecutive_negative_emotions = max(0, self.consecutive_negative_emotions - 1)
            self.consecutive_positive_emotions = max(0, self.consecutive_positive_emotions - 1)

        # Apply adjustment with smoothing
        self.emotion_component = self._smooth_update(
            self.emotion_component,
            self.emotion_component + adjustment,
            0, 50  # Clamp to 0-50 range
        )

        self._recalculate_pressure()

    def update_performance(
        self,
        answer_score: Optional[float] = None,
        response_time_seconds: Optional[float] = None
    ) -> None:
        """
        Update pressure based on performance metrics.

        Args:
            answer_score: Score from 1-10 for the answer
            response_time_seconds: Time taken to respond in seconds
        """
        adjustment = 0

        # Process answer score
        if answer_score is not None:
            self.answer_scores.append(answer_score)
            self.answer_scores = self.answer_scores[-10:]  # Keep last 10

            if answer_score < 5:
                # Low score increases pressure
                self.consecutive_low_scores += 1
                self.consecutive_high_scores = 0
                adjustment += (5 - answer_score) * 1.5

                if self.consecutive_low_scores > 2:
                    adjustment *= 1.3
            elif answer_score >= 7:
                # High score reduces pressure
                self.consecutive_high_scores += 1
                self.consecutive_low_scores = 0
                adjustment -= (answer_score - 6) * 1.2

                if self.consecutive_high_scores > 2:
                    adjustment *= 1.2
            else:
                # Average score, slight reduction
                adjustment -= 0.5
                self.consecutive_low_scores = max(0, self.consecutive_low_scores - 1)
                self.consecutive_high_scores = max(0, self.consecutive_high_scores - 1)

        # Process response time
        if response_time_seconds is not None:
            self.response_times.append(response_time_seconds)
            self.response_times = self.response_times[-10:]

            # Response time benchmarks (seconds)
            if response_time_seconds > 120:  # > 2 minutes
                adjustment += 3  # Long response increases pressure
            elif response_time_seconds < 10:  # < 10 seconds
                adjustment += 2  # Very short might indicate rushing
            elif 30 <= response_time_seconds <= 90:
                adjustment -= 1  # Good timing reduces pressure

        # Apply adjustment
        self.performance_component = self._smooth_update(
            self.performance_component,
            self.performance_component + adjustment,
            0, 50
        )

        self._recalculate_pressure()

    def _smooth_update(
        self,
        current: float,
        target: float,
        min_val: float,
        max_val: float
    ) -> float:
        """Apply smoothed update with clamping."""
        new_value = current + (target - current) * self.smoothing_factor
        return max(min_val, min(max_val, new_value))

    def _recalculate_pressure(self) -> None:
        """Recalculate total pressure from components."""
        self.pressure_level = self.emotion_component + self.performance_component
        self.pressure_level = max(0, min(100, self.pressure_level))

    def get_current_difficulty(self) -> DifficultyLevel:
        """Get current difficulty level based on pressure."""
        for (low, high), difficulty in self.DIFFICULTY_RANGES.items():
            if low <= self.pressure_level < high:
                return difficulty
        return DifficultyLevel.MEDIUM

    def get_current_zone(self) -> PressureZone:
        """Get current pressure zone."""
        for (low, high), zone in self.ZONE_RANGES.items():
            if low <= self.pressure_level < high:
                return zone
        return PressureZone.GROWTH

    def get_pressure_feedback(self) -> str:
        """Get feedback message based on current state."""
        zone = self.get_current_zone()
        difficulty = self.get_current_difficulty()

        if zone == PressureZone.COMFORT:
            return "You're doing well! Let's increase the challenge slightly."
        elif zone == PressureZone.GROWTH:
            return "Great balance! You're in the optimal learning zone."
        else:  # CHALLENGE
            if self.consecutive_negative_emotions > 3:
                return "Take a deep breath. Let's ease up a bit to help you refocus."
            return "You're being challenged! Stay focused and confident."

    def get_tips(self) -> List[str]:
        """Get actionable tips based on current state."""
        tips = []
        zone = self.get_current_zone()

        # Emotion-based tips
        if self.consecutive_negative_emotions > 2:
            tips.append("Try taking a slow, deep breath before answering.")
            tips.append("Remember: it's okay to pause and collect your thoughts.")

        # Performance-based tips
        if self.consecutive_low_scores > 1:
            tips.append("Use the STAR method: Situation, Task, Action, Result.")
            tips.append("Try to include specific examples from your experience.")

        if self.response_times and self.response_times[-1] > 120:
            tips.append("Keep answers concise - aim for 1-2 minutes per response.")

        if self.response_times and self.response_times[-1] < 15:
            tips.append("Don't rush! Take time to formulate a complete answer.")

        # Zone-based tips
        if zone == PressureZone.CHALLENGE:
            tips.append("Focus on your strengths and past successes.")
            tips.append("It's okay to ask for clarification if needed.")

        return tips[:3]  # Return max 3 tips

    def get_state(self) -> PressureState:
        """Get complete current pressure state."""
        return PressureState(
            pressure_level=round(self.pressure_level, 1),
            difficulty=self.get_current_difficulty(),
            zone=self.get_current_zone(),
            emotion_component=round(self.emotion_component, 1),
            performance_component=round(self.performance_component, 1),
            feedback=self.get_pressure_feedback(),
            tips=self.get_tips()
        )

    def get_stats(self) -> Dict:
        """Get pressure statistics for the session."""
        avg_score = sum(self.answer_scores) / len(self.answer_scores) if self.answer_scores else 0
        avg_time = sum(self.response_times) / len(self.response_times) if self.response_times else 0

        # Calculate emotion distribution
        emotion_counts = {}
        for entry in self.emotion_history:
            emotion = entry["emotion"]
            emotion_counts[emotion] = emotion_counts.get(emotion, 0) + 1

        return {
            "current_pressure": round(self.pressure_level, 1),
            "current_difficulty": self.get_current_difficulty().value,
            "current_zone": self.get_current_zone().value,
            "average_score": round(avg_score, 1),
            "average_response_time": round(avg_time, 1),
            "questions_answered": len(self.answer_scores),
            "emotion_distribution": emotion_counts,
            "consecutive_negative_emotions": self.consecutive_negative_emotions,
            "consecutive_positive_emotions": self.consecutive_positive_emotions,
        }

    def reset(self) -> None:
        """Reset pressure manager to initial state."""
        self._init_pressure_from_difficulty()
        self.emotion_history.clear()
        self.answer_scores.clear()
        self.response_times.clear()
        self.consecutive_negative_emotions = 0
        self.consecutive_positive_emotions = 0
        self.consecutive_low_scores = 0
        self.consecutive_high_scores = 0


# Singleton management for session-based pressure managers
_pressure_managers: Dict[str, PressureManager] = {}


def get_pressure_manager(
    session_id: str,
    base_difficulty: str = "medium"
) -> PressureManager:
    """
    Get or create a pressure manager for a session.

    Args:
        session_id: Unique session identifier
        base_difficulty: Starting difficulty for new sessions

    Returns:
        PressureManager instance for the session
    """
    if session_id not in _pressure_managers:
        _pressure_managers[session_id] = PressureManager(base_difficulty=base_difficulty)
    return _pressure_managers[session_id]


def clear_pressure_manager(session_id: str) -> None:
    """Remove pressure manager for a session."""
    _pressure_managers.pop(session_id, None)


def get_all_active_sessions() -> List[str]:
    """Get list of all active session IDs with pressure managers."""
    return list(_pressure_managers.keys())
