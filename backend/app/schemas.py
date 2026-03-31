"""
Pydantic Schemas
================
Request/Response validation models for the API.
"""

from datetime import datetime
from typing import Optional, Dict, List, Any
from pydantic import BaseModel, Field, ConfigDict


# ============================================================================
# Session Schemas
# ============================================================================

class SessionCreate(BaseModel):
    """Request schema for creating a new interview session."""
    user_id: Optional[str] = None
    job_role: str = Field(default="Software Engineer", max_length=200)
    subject: str = Field(default="General", max_length=100)
    difficulty: str = Field(default="medium", pattern="^(easy|medium|hard)$")


class SessionResponse(BaseModel):
    """Response schema for session data."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: Optional[str]
    job_role: str
    subject: str
    difficulty: str
    status: str
    transcript: Optional[List[Dict[str, Any]]] = None
    avg_confidence_score: float
    avg_emotion_score: float
    overall_score: float
    total_questions: int
    total_frames_analyzed: int
    emotion_distribution: Optional[Dict[str, float]]
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime]


class SessionSummary(BaseModel):
    """Summary response for completed sessions."""
    session_id: str
    duration_minutes: float
    total_questions: int
    avg_confidence: float
    dominant_emotion: str
    emotion_breakdown: Dict[str, float]
    performance_rating: str
    recommendations: List[str]


# ============================================================================
# Question Schemas
# ============================================================================

class QuestionRequest(BaseModel):
    """Request for next interview question."""
    session_id: str
    previous_answer: Optional[str] = None
    emotion_context: Optional[Dict[str, float]] = None
    metrics_context: Optional[Dict[str, float]] = None


class QuestionResponse(BaseModel):
    """Response containing the interview question."""
    question_number: int
    question_text: str
    question_type: str
    tips: Optional[List[str]] = None


class AnswerSubmit(BaseModel):
    """Submit an answer to a question."""
    session_id: str
    question_number: int
    answer_text: str
    duration_seconds: Optional[float] = None


class AnswerFeedback(BaseModel):
    """AI feedback on the submitted answer."""
    score: float = Field(ge=0.0, le=10.0)
    clarity_score: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    content_score: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    feedback: str
    golden_answer: Optional[str] = None
    comparison: Optional[str] = None
    strengths: List[str]
    improvements: List[str]
    follow_up_suggested: bool


# ============================================================================
# Emotion/Inference Schemas
# ============================================================================

class EmotionPrediction(BaseModel):
    """Single emotion prediction result."""
    emotion: str
    confidence: float = Field(ge=0.0, le=1.0)
    all_probabilities: Dict[str, float]
    inference_time_ms: float


class FrameAnalysisRequest(BaseModel):
    """Request for analyzing a video frame."""
    session_id: str
    frame_base64: str
    question_number: Optional[int] = None


class FrameAnalysisResponse(BaseModel):
    """Response from frame analysis."""
    success: bool
    emotion: Optional[EmotionPrediction] = None
    posture: Optional[str] = None
    eye_contact: Optional[str] = None
    head_pose: Optional[Dict[str, float]] = None
    gaze_ratio: Optional[float] = None
    error: Optional[str] = None


class WebSocketMessage(BaseModel):
    """Generic WebSocket message structure."""
    type: str  # "frame", "emotion", "error", "ping", "pong"
    payload: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ============================================================================
# Health & Status Schemas
# ============================================================================

class HealthCheck(BaseModel):
    """Health check response."""
    status: str
    version: str
    gpu_available: bool
    gpu_name: Optional[str]
    model_loaded: bool
    database_connected: bool


class InferenceStatus(BaseModel):
    """Inference service status."""
    model_loaded: bool
    blendshape_fallback: Optional[bool] = None
    fer_active: Optional[bool] = None
    device: str
    model_architecture: str
    warm: bool  # Has processed at least one frame
    total_inferences: int
    avg_inference_time_ms: float


# ============================================================================
# Error Schemas
# ============================================================================

class ErrorResponse(BaseModel):
    """Standard error response."""
    error: str
    detail: Optional[str] = None
    code: Optional[str] = None
