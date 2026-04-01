"""
Interview History Router
========================
Save completed interview reports and retrieve past sessions per user.
"""

from typing import List

from fastapi import APIRouter, HTTPException, status

from app import database as db
from app.models import InterviewSession

router = APIRouter(prefix="/history", tags=["Interview History"])


# ============================================================================
# POST /history/save
# ============================================================================

@router.post("/save")
async def save_session(session: InterviewSession):
    """
    Persist interview results once a session ends.
    Accepts an InterviewSession body and inserts it into db.sessions_collection.
    """
    if db.sessions_collection is None:
        raise HTTPException(status_code=503, detail="Database not connected")
    doc = session.model_dump()
    result = await db.sessions_collection.insert_one(doc)

    return {
        "msg": "Session saved successfully",
        "session_id": str(result.inserted_id),
    }


# ============================================================================
# GET /history/user/{user_id}
# ============================================================================

@router.get("/user/{user_id}")
async def get_user_history(user_id: str):
    """
    Return every past interview for a given student,
    sorted newest-first.
    """
    if db.sessions_collection is None:
        raise HTTPException(status_code=503, detail="Database not connected")
    # Sort by created_at (interview router) falling back to timestamp (manual saves)
    cursor = db.sessions_collection.find({"user_id": user_id}).sort("created_at", -1)
    sessions = await cursor.to_list(length=100)

    # Filter out empty/abandoned sessions to keep history clean (session-wise)
    from app.database import session_serializer
    valid_sessions = []
    for s in sessions:
        # A session is valid if it's 'completed', 'in_progress', or has at least one question generated
        questions = s.get("questions", [])
        if s.get("status") in ["completed", "in_progress"] or len(questions) > 0:
            valid_sessions.append(session_serializer(s))

    return valid_sessions
