"""
Admin Router
=============
Provides platform-wide statistics and user management for admin users.
Requires valid JWT with admin role.
"""

from fastapi import APIRouter, Depends, HTTPException

from app import database as db
from app.routers.auth import get_current_user

router = APIRouter(prefix="/admin", tags=["Admin"])


def _require_admin(current_user: dict):
    """Raise 403 if the user is not an admin."""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")


@router.get("/stats")
async def get_admin_stats(current_user: dict = Depends(get_current_user)):
    """Return aggregate platform statistics."""
    _require_admin(current_user)
    if db.users_collection is None or db.sessions_collection is None:
        raise HTTPException(status_code=503, detail="Database not connected")

    # Fetch all users
    all_users = await db.users_collection.find({}).sort("_id", -1).to_list(length=10000)
    total_users = len(all_users)

    # Count by role
    users_by_role = {}
    recent_signups = 0
    for u in all_users:
        role = u.get("role", "student")
        users_by_role[role] = users_by_role.get(role, 0) + 1

    # Fetch all sessions
    all_sessions = await db.sessions_collection.find({}).sort("created_at", -1).to_list(length=10000)
    total_sessions = len(all_sessions)

    completed_sessions = sum(
        1 for s in all_sessions if s.get("status") == "completed"
    )

    # Average score
    scores = []
    sessions_by_difficulty = {}
    for s in all_sessions:
        if s.get("overall_score") is not None:
            scores.append(s["overall_score"])
        diff = s.get("difficulty", "medium")
        sessions_by_difficulty[diff] = sessions_by_difficulty.get(diff, 0) + 1

    average_score = sum(scores) / len(scores) if scores else 0.0

    return {
        "total_users": total_users,
        "total_sessions": total_sessions,
        "completed_sessions": completed_sessions,
        "average_score": average_score,
        "recent_signups": len(all_users[-7:]) if total_users > 0 else 0,
        "users_by_role": users_by_role,
        "sessions_by_difficulty": sessions_by_difficulty,
    }


@router.get("/users")
async def get_admin_users(limit: int = 10, current_user: dict = Depends(get_current_user)):
    """Return the most recent users."""
    _require_admin(current_user)
    if db.users_collection is None:
        raise HTTPException(status_code=503, detail="Database not connected")

    all_users = await db.users_collection.find({}).sort("_id", -1).to_list(length=limit)

    result = []
    for u in all_users:
        result.append({
            "id": str(u.get("_id", "")),
            "username": u.get("username", "Unknown"),
            "email": u.get("email", ""),
            "role": u.get("role", "student"),
            "created_at": str(u.get("created_at", "")),
        })

    return result
