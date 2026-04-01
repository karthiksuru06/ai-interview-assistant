"""
Data Models (Pydantic)
======================
Validation schemas for requests, responses, and database documents.
"""

from datetime import datetime
from typing import Optional, Dict, List, Any

from pydantic import BaseModel, Field, EmailStr


# ============================================================================
# Auth — Tokens
# ============================================================================

class Token(BaseModel):
    """JWT token returned after successful login."""
    access_token: str
    token_type: str = "bearer"
    role: str


# ============================================================================
# Auth — Request Bodies
# ============================================================================

class UserSignup(BaseModel):
    """Payload for POST /auth/signup."""
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(
        ...,
        min_length=8,
        max_length=100,
        description="Must contain at least one uppercase, one lowercase, and one digit",
    )
    security_question: str = Field(..., min_length=3, max_length=255)
    security_answer: str = Field(..., min_length=2, max_length=100)

    @classmethod
    def _validate_password_complexity(cls, v: str) -> str:
        import re
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one digit")
        return v

    def model_post_init(self, __context) -> None:
        self._validate_password_complexity(self.password)


class UserLogin(BaseModel):
    """Payload for POST /auth/login."""
    email: EmailStr
    password: str


class PasswordReset(BaseModel):
    """Payload for POST /auth/reset-password."""
    email: EmailStr
    security_answer: str
    new_password: str = Field(..., min_length=8, max_length=100)

    def model_post_init(self, __context) -> None:
        UserSignup._validate_password_complexity(self.new_password)


# ============================================================================
# Auth — Internal DB Representation
# ============================================================================

class UserInDB(BaseModel):
    """
    Full user document as stored in the database.
    Extends the signup fields with server-side data.
    """
    username: str
    email: str
    hashed_password: str
    security_question: str
    security_answer_hash: str
    role: str = "student"
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ============================================================================
# Interview Session
# ============================================================================

class InterviewSession(BaseModel):
    """Schema for a completed interview session stored in the database."""
    user_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    subject: str = "General"
    difficulty: str = "medium"
    overall_score: int = 0
    metrics: Dict[str, Any] = Field(default_factory=dict)
    transcript: List[Dict[str, Any]] = Field(default_factory=list)
    questions: List[Dict[str, Any]] = Field(default_factory=list)
    status: str = "completed"
