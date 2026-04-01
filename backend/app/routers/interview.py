"""
Interview Router
=================
REST endpoints and WebSocket for interview management and real-time analysis.
"""

import asyncio
import json
import time
from datetime import datetime
from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request, WebSocket, WebSocketDisconnect, status

from app.config import settings
from app import database as db
import logging

logger = logging.getLogger(__name__)
from app.schemas import (
    SessionCreate,
    SessionSummary,
    QuestionRequest,
    QuestionResponse,
    AnswerSubmit,
    AnswerFeedback,
    FrameAnalysisRequest,
    FrameAnalysisResponse,
    EmotionPrediction,
)
from app.services.gemini import get_gemini_service

# Inference service is optional — model may not be present
try:
    from app.services.inference import get_inference_service
    _inference_available = True
except Exception:
    _inference_available = False

from app.services.audio import get_audio_service


router = APIRouter(prefix="/interview", tags=["Interview"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _session_to_dict(doc: dict) -> dict:
    """Normalise a session document for JSON responses."""
    if doc and "_id" in doc:
        doc["id"] = str(doc["_id"])
        del doc["_id"]
    return doc


# ============================================================================
# Comparison Helper
# ============================================================================

async def _fetch_previous_session_score(user_id: str, current_session_id: str) -> Optional[Dict]:
    """
    Fetch the most recent completed session for this user (excluding current).
    Returns {"overall_score": float, "avg_confidence": float, "subject": str}
    or None if no prior session exists.
    """
    if db.sessions_collection is None or not user_id:
        return None
    try:
        cursor = db.sessions_collection.find({
            "user_id": user_id,
            "status": "completed",
            "_id": {"$ne": current_session_id},
        }).sort("completed_at", -1)
        sessions = await cursor.to_list(length=1)
        if sessions:
            prev = sessions[0]
            return {
                "overall_score": prev.get("overall_score", 0),
                "avg_confidence": prev.get("avg_confidence_score", 0),
                "subject": prev.get("subject", ""),
                "difficulty": prev.get("difficulty", ""),
            }
    except Exception as e:
        logger.warning(f"[COMPARISON] Failed to fetch previous session: {e}")
    return None


def _build_comparison_text(
    current_avg: float,
    previous_data: Optional[Dict],
) -> Optional[str]:
    """Build a human-readable comparison string."""
    if previous_data is None:
        return None
    prev_score = previous_data["overall_score"]
    diff = current_avg - prev_score
    if diff > 0:
        return (f"User improved by {abs(diff):.1f} points since last session "
                f"(previous: {prev_score:.1f}/10, current avg: {current_avg:.1f}/10)")
    elif diff < 0:
        return (f"User declined by {abs(diff):.1f} points since last session "
                f"(previous: {prev_score:.1f}/10, current avg: {current_avg:.1f}/10)")
    return (f"User is performing at the same level as last session "
            f"({prev_score:.1f}/10)")


# ============================================================================
# Session Management
# ============================================================================

@router.post("/start_session", status_code=status.HTTP_201_CREATED)
async def start_session(request: SessionCreate):
    """
    Initialise a new interview session.
    Returns the session ID for subsequent requests.
    """
    if db.sessions_collection is None:
        raise HTTPException(status_code=503, detail="Database not connected")

    now = datetime.utcnow()
    session_doc = {
        "user_id": request.user_id,
        "job_role": request.job_role,
        "subject": request.subject,
        "difficulty": request.difficulty,
        "status": "created",
        "transcript": [],
        "questions": [],
        "avg_confidence_score": 0.0,
        "avg_emotion_score": 0.0,
        "overall_score": 0.0,
        "total_questions": 0,
        "total_frames_analyzed": 0,
        "emotion_distribution": {},
        "created_at": now,
        "updated_at": now,
        "completed_at": None,
    }

    result = await db.sessions_collection.insert_one(session_doc)
    session_doc["id"] = str(result.inserted_id)

    return {
        "id": session_doc["id"],
        "user_id": request.user_id,
        "job_role": request.job_role,
        "subject": request.subject,
        "difficulty": request.difficulty,
        "status": "created",
        "msg": "Session created",
    }


@router.get("/session/{session_id}")
async def get_session_details(session_id: str):
    """Get details of an interview session."""
    if db.sessions_collection is None:
        raise HTTPException(status_code=503, detail="Database not connected")

    try:
        doc = await db.sessions_collection.find_one({"_id": session_id})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid session ID format")

    if not doc:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    return _session_to_dict(doc)


@router.post("/session/{session_id}/end")
async def end_session(session_id: str):
    """
    End an interview session, calculate summary, and persist the report.
    """
    if db.sessions_collection is None:
        raise HTTPException(status_code=503, detail="Database not connected")

    try:
        doc = await db.sessions_collection.find_one({"_id": session_id})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid session ID format")

    if not doc:
        raise HTTPException(status_code=404, detail="Session not found")

    now = datetime.utcnow()
    questions = doc.get("questions", [])

    # Build Q&A pairs for the summary
    qa_pairs = [
        {
            "question": q.get("question_text", ""),
            "answer": q.get("user_response", ""),
            "score": q.get("ai_score", 5.0),
        }
        for q in questions
    ]

    # ── Comparison: fetch previous session ──
    user_id = doc.get("user_id", "")
    previous_session = await _fetch_previous_session_score(user_id, session_id)
    scored_qs = [q for q in questions if q.get("ai_score") is not None]
    current_avg = (sum(q["ai_score"] for q in scored_qs) / len(scored_qs)) if scored_qs else 0
    comparison_text = _build_comparison_text(current_avg, previous_session)

    # Generate AI summary (falls back gracefully if Gemini is unavailable)
    gemini = get_gemini_service()
    summary_data = await gemini.generate_session_summary(
        job_role=doc.get("job_role", "Software Engineer"),
        questions_and_answers=qa_pairs,
        overall_emotion_data=doc.get("emotion_distribution", {}),
        comparison_text=comparison_text,
    )

    # Calculate duration
    created = doc.get("created_at", now)
    duration = (now - created).total_seconds() / 60 if created else 0

    # Dominant emotion
    emotion_dist = doc.get("emotion_distribution", {})
    dominant_emotion = max(emotion_dist, key=emotion_dist.get) if emotion_dist else "neutral"

    # Update the session in DB
    await db.sessions_collection.update_one(
        {"_id": session_id},
        {
            "$set": {
                "status": "completed",
                "completed_at": now,
                "updated_at": now,
                "overall_score": summary_data.get("overall_score", 0),
                "avg_confidence_score": round(current_avg, 2),
                "performance_rating": summary_data.get("performance_rating", "Average"),
            }
        },
    )

    return {
        "session_id": session_id,
        "duration_minutes": round(duration, 1),
        "total_questions": len(questions),
        "avg_confidence": doc.get("avg_confidence_score", 0.0),
        "dominant_emotion": dominant_emotion,
        "emotion_breakdown": emotion_dist,
        "performance_rating": summary_data.get("performance_rating", "Average"),
        "recommendations": summary_data.get("specific_recommendations", []),
    }


# ============================================================================
# Question Management
# ============================================================================

@router.post("/next_question", response_model=QuestionResponse)
async def get_next_question(request: QuestionRequest):
    """
    Get the next interview question.
    Uses Gemini AI with graceful fallback to a static question bank.
    """
    if db.sessions_collection is None:
        raise HTTPException(status_code=503, detail="Database not connected")

    try:
        doc = await db.sessions_collection.find_one({"_id": request.session_id})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid session ID")

    if not doc:
        raise HTTPException(status_code=404, detail="Session not found")

    # Prevent duplicate question generation from concurrent requests
    # 1. Look for an existing, unanswered question asked within the last 10 seconds
    questions = doc.get("questions", [])
    if questions and not request.previous_answer:
        last_q = questions[-1]
        if last_q.get("user_response") is None:
            # Check if asked_at is very recent
            asked_at_str = last_q.get("asked_at")
            if asked_at_str:
                try:
                    # Handle ISO format with 'Z' for UTC
                    iso_str = asked_at_str.replace("Z", "+00:00")
                    asked_at = datetime.fromisoformat(iso_str)
                    
                    # We use UTC for everything
                    now_utc = datetime.utcnow()
                    # Ensure asked_at is offset-naive if now_utc is naive
                    if asked_at.tzinfo is not None:
                        asked_at = asked_at.replace(tzinfo=None)
                        
                    delta = (now_utc - asked_at).total_seconds()
                    if delta < 10:  # 10s window to catch double-clicks
                        logger.info(f"[INTERVIEW] Duplicate next_question detected. Returning existing Q{last_q['question_number']}")
                        return QuestionResponse(
                            question_number=last_q["question_number"],
                            question_text=last_q["question_text"],
                            question_type=last_q["question_type"],
                            tips=last_q.get("tips"),
                        )
                except Exception as e:
                    logger.warning(f"Failed to check duplicate question: {e}")

    # Save and evaluate previous answer if provided
    if request.previous_answer and questions:
        q_idx = len(questions) - 1
        questions[q_idx]["user_response"] = request.previous_answer
        questions[q_idx]["answered_at"] = datetime.utcnow().isoformat()
        
        # Evaluate it now so it's not lost
        try:
            gemini = get_gemini_service()
            evaluation = await gemini.evaluate_answer(
                question=questions[q_idx]["question_text"],
                answer=request.previous_answer,
                job_role=doc.get("job_role", "Software Engineer")
            )
            questions[q_idx]["ai_feedback"] = evaluation["feedback"]
            questions[q_idx]["ai_score"] = evaluation["score"]
            questions[q_idx]["clarity_score"] = evaluation.get("clarity_score")
            questions[q_idx]["content_score"] = evaluation.get("content_score")
        except Exception as e:
            logger.warning(f"Failed to evaluate skipped question: {e}")

    # Extract previous answer score for adaptive question generation
    previous_answer_score = None
    if questions and questions[-1].get("ai_score") is not None:
        previous_answer_score = float(questions[-1]["ai_score"])

    question_number = len(questions) + 1
    previous_q_texts = [q.get("question_text", "") for q in questions]

    gemini = get_gemini_service()
    question_data = await gemini.generate_question(
        job_role=doc.get("job_role", "Software Engineer"),
        difficulty=doc.get("difficulty", "medium"),
        question_number=question_number,
        previous_questions=previous_q_texts,
        previous_answer=request.previous_answer,
        emotion_context=request.emotion_context,
        subject=doc.get("subject"),
        metrics_context=request.metrics_context,
        previous_answer_score=previous_answer_score,
    )

    # Append new question to the session
    new_question = {
        "question_number": question_data["question_number"],
        "question_text": question_data["question_text"],
        "question_type": question_data["question_type"],
        "user_response": None,
        "ai_feedback": None,
        "ai_score": None,
        "asked_at": datetime.utcnow().isoformat(),
        "answered_at": None,
    }
    questions.append(new_question)

    # Update session in-place
    await db.sessions_collection.update_one(
        {"_id": request.session_id},
        {
            "$set": {
                "questions": questions,
                "total_questions": question_number,
                "status": "in_progress",
                "updated_at": datetime.utcnow(),
            }
        },
    )

    return QuestionResponse(
        question_number=question_data["question_number"],
        question_text=question_data["question_text"],
        question_type=question_data["question_type"],
        tips=question_data.get("tips"),
    )


@router.post("/submit_answer", response_model=AnswerFeedback)
async def submit_answer(request: AnswerSubmit):
    """
    Submit an answer and receive AI-powered feedback.
    """
    if db.sessions_collection is None:
        raise HTTPException(status_code=503, detail="Database not connected")

    try:
        doc = await db.sessions_collection.find_one({"_id": request.session_id})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid session ID")

    if not doc:
        raise HTTPException(status_code=404, detail="Session not found")

    # Find the matching question
    q_idx = next((i for i, q in enumerate(questions) if q.get("question_number") == request.question_number), None)

    if q_idx is None:
        raise HTTPException(status_code=404, detail="Question not found")

    # 1. Commit the user response to DB immediately (Persistence First)
    # This prevents data loss if evaluation fails/timeouts
    questions[q_idx]["user_response"] = request.answer_text
    questions[q_idx]["answered_at"] = datetime.utcnow().isoformat()
    questions[q_idx]["response_duration_seconds"] = request.duration_seconds
    
    await db.sessions_collection.update_one(
        {"_id": request.session_id},
        {"$set": {"questions": questions, "updated_at": datetime.utcnow()}},
    )

    # 2. Evaluate with AI
    user_id = doc.get("user_id", "")
    previous_session = await _fetch_previous_session_score(user_id, request.session_id)
    scored_qs = [q for q in questions if q.get("ai_score") is not None]
    current_avg = (sum(q["ai_score"] for q in scored_qs) / len(scored_qs)) if scored_qs else 5.0
    comparison_text = _build_comparison_text(current_avg, previous_session)

    try:
        gemini = get_gemini_service()
        evaluation = await gemini.evaluate_answer(
            question=questions[q_idx]["question_text"],
            answer=request.answer_text,
            job_role=doc.get("job_role", "Software Engineer"),
            comparison_text=comparison_text,
        )

        # Update the question entry with feedback
        questions[q_idx]["ai_feedback"] = evaluation["feedback"]
        questions[q_idx]["ai_score"] = evaluation["score"]
        questions[q_idx]["clarity_score"] = evaluation.get("clarity_score")
        questions[q_idx]["content_score"] = evaluation.get("content_score")

        await db.sessions_collection.update_one(
            {"_id": request.session_id},
            {"$set": {"questions": questions, "updated_at": datetime.utcnow()}},
        )

        return AnswerFeedback(
            score=evaluation["score"],
            clarity_score=evaluation.get("clarity_score"),
            content_score=evaluation.get("content_score"),
            feedback=evaluation["feedback"],
            golden_answer=evaluation.get("golden_answer"),
            comparison=evaluation.get("comparison"),
            strengths=evaluation["strengths"],
            improvements=evaluation["improvements"],
            follow_up_suggested=evaluation["follow_up_suggested"],
        )
    except Exception as e:
        logger.error(f"[INTERVIEW] Feedback generation failed: {e}")
        # Return a partial response but at least we saved the answer text!
        return AnswerFeedback(
            score=5.0,
            feedback="Your response was recorded, but AI evaluation is temporarily unavailable.",
            strengths=[],
            improvements=[],
            follow_up_suggested=False
        )


# ============================================================================
# Frame Analysis (REST)
# ============================================================================

@router.post("/analyze_frame", response_model=FrameAnalysisResponse)
async def analyze_frame(request: FrameAnalysisRequest):
    """
    Analyze a single video frame for emotion detection.
    Returns a mock result if the FER model is not loaded.
    """
    if not _inference_available:
        return FrameAnalysisResponse(success=False, error="Inference service not available")

    inference = get_inference_service()

    # Check if any FER method is available (PyTorch model OR blendshape fallback)
    fer_available = inference.model is not None or (
        inference.blendshape_fer is not None and inference.blendshape_fer.is_available
    )

    if not fer_available:
        if not settings.ai_safe_mode:
            logger.error("[FER] No FER method available and AI_SAFE_MODE=false")
            return FrameAnalysisResponse(success=False, error="FER model not loaded (AI_SAFE_MODE=false)")
        # Safe-mode: return a mock/placeholder when no FER available
        return FrameAnalysisResponse(
            success=True,
            emotion=EmotionPrediction(
                emotion="neutral",
                confidence=0.5,
                all_probabilities={
                    "neutral": 0.5, "happiness": 0.1, "surprise": 0.05,
                    "sadness": 0.05, "anger": 0.05, "disgust": 0.05,
                    "fear": 0.05, "contempt": 0.15,
                },
                inference_time_ms=0.0,
            ),
        )

    # predict() will use PyTorch model if loaded, else blendshape fallback
    result = inference.predict_from_base64(request.frame_base64)

    if not result["success"]:
        return FrameAnalysisResponse(
            success=False,
            error=result.get("error", "Inference failed"),
            posture=result.get("posture"),
            eye_contact=result.get("eye_contact"),
            head_pose=result.get("head_pose"),
            gaze_ratio=result.get("gaze_ratio"),
        )

    return FrameAnalysisResponse(
        success=True,
        emotion=EmotionPrediction(
            emotion=result["emotion"],
            confidence=result["confidence"],
            all_probabilities=result["all_probabilities"],
            inference_time_ms=result["inference_time_ms"],
        ),
        posture=result.get("posture"),
        eye_contact=result.get("eye_contact"),
        head_pose=result.get("head_pose"),
        gaze_ratio=result.get("gaze_ratio"),
    )


# ============================================================================
# WebSocket for Real-Time Inference
# ============================================================================

class ConnectionManager:
    """Manage WebSocket connections."""

    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, session_id: str):
        self.active_connections[session_id] = websocket

    def disconnect(self, session_id: str):
        self.active_connections.pop(session_id, None)

    async def send_json(self, session_id: str, data: dict):
        if session_id in self.active_connections:
            await self.active_connections[session_id].send_json(data)


manager = ConnectionManager()


# ── Simple transcribe rate limiter ──
import time as _time
from collections import defaultdict as _defaultdict
_transcribe_buckets: dict[str, list[float]] = _defaultdict(list)


def _check_transcribe_rate(ip: str):
    now = _time.time()
    bucket = _transcribe_buckets[ip]
    _transcribe_buckets[ip] = bucket = [t for t in bucket if now - t < 60]
    if len(bucket) >= settings.rate_limit_transcribe_per_minute:
        raise HTTPException(status_code=429, detail="Transcription rate limit exceeded")
    bucket.append(now)


# ── REST Audio Transcription Endpoint ──────────────────────────
@router.post("/transcribe")
async def transcribe_audio(request: Request):
    """
    Transcribe an audio recording (base64 WebM/Opus) via Whisper.
    Used by the Record/Stop UI for reliable transcription.
    """
    _check_transcribe_rate(request.client.host)
    try:
        body = await request.json()
        audio_data = body.get("audio")
        if not audio_data:
            raise HTTPException(status_code=400, detail="No audio data provided")

        audio_service = get_audio_service()
        result = await asyncio.to_thread(
            audio_service.analyze_from_base64, audio_data, True
        )

        transcript = result.get("transcript") or ""
        return {
            "success": True,
            "transcript": transcript,
            "clarity": result.get("clarity"),
            "fluency": result.get("fluency"),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Transcribe] Failed: {e}")
        return {"success": False, "transcript": "", "error": str(e)}


@router.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str, token: str = ""):
    """
    Real-time WebSocket endpoint for video frame analysis.

    Authentication: pass JWT as ``?token=<jwt>`` query parameter.

    Protocol:
    - Client sends: {"type": "frame", "data": "<base64_image>", "question_number": 1}
    - Server responds: {"type": "emotion", "data": {...emotion_prediction...}}
    """
    from jose import jwt as _jwt, JWTError as _JWTError

    print(f"[WS] Connection attempt for session: {session_id}")

    # ── Authenticate via query-param JWT ──
    ws_user_id: str | None = None
    if token:
        try:
            payload = _jwt.decode(
                token,
                settings.jwt_secret_key,
                algorithms=[settings.jwt_algorithm],
            )
            ws_user_id = payload.get("sub")
        except _JWTError:
            logger.warning("[WS] Invalid JWT token — rejecting connection")
            await websocket.close(code=4001)
            return
    # If no token supplied we still allow the connection for backward compat
    # but log a warning so operators notice unauthenticated streams.
    if ws_user_id is None:
        logger.warning(f"[WS] Unauthenticated connection for session {session_id}")

    try:
        await websocket.accept()
        print(f"[WS] Connection accepted: {session_id}")
    except Exception as e:
        print(f"[WS] Accept failed: {e}")
        return

    # Look up session
    try:
        sid = session_id
        session_data = await db.sessions_collection.find_one({"_id": sid})
        if not session_data:
            print(f"[WS] Session not found: {session_id} (converted: {sid})")
            await websocket.close(code=4004)
            return

        # Verify session ownership when token is present
        if ws_user_id and session_data.get("user_id") and session_data["user_id"] != ws_user_id:
            logger.warning(f"[WS] User {ws_user_id} tried to access session owned by {session_data['user_id']}")
            await websocket.close(code=4003)
            return

        print(f"[WS] Session found for {session_id}")
    except Exception as e:
        print(f"[WS] Session lookup failed: {e}")
        await websocket.close()
        return

    inference = get_inference_service()
    # verify model is loaded
    if inference.model is None and not settings.ai_safe_mode:
         print("[WS] AI Model not loaded!")
         # optionally close or warn
    
    await manager.connect(websocket, session_id)

    frames_processed = 0
    total_latency = 0.0
    emotion_counts = {}  # Track cumulative emotion distribution
    _emotion_save_counter = 0  # Save to DB every N frames
    _last_frame_time = 0.0  # For backpressure — drop frames if processing is behind
    _MIN_FRAME_INTERVAL_MS = 200  # Process at most 5 frames/sec

    try:
        while True:
            raw_data = await websocket.receive_text()

            try:
                message = json.loads(raw_data)
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "error": "Invalid JSON"})
                continue

            msg_type = message.get("type")

            if msg_type == "ping":
                await websocket.send_json({"type": "pong"})
                continue

            # ── Silence Gate ──────────────────────────────────────
            # Client sends {"type": "silence"} when mic is off or
            # audio RMS is below threshold.  Return immediately —
            # no GPU / Gemini / Vision processing needed.
            if msg_type == "silence":
                await websocket.send_json({
                    "type": "silence",
                    "metrics": 0,
                })
                continue

            # ── Browser-Side Metrics ─────────────────────────────
            # Client runs MediaPipe in-browser and sends pre-computed
            # metrics periodically. No video frames are transmitted.
            if msg_type == "metrics":
                data = message.get("data", {})
                detected_emotion = data.get("emotion", "neutral")
                emotion_counts[detected_emotion] = emotion_counts.get(detected_emotion, 0) + 1
                frames_processed += 1

                # Persist to DB every 10 metric reports
                _emotion_save_counter += 1
                if _emotion_save_counter >= 10:
                    _emotion_save_counter = 0
                    try:
                        total = sum(emotion_counts.values())
                        emotion_dist = {k: round(v / total, 4) for k, v in emotion_counts.items()}
                        await db.sessions_collection.update_one(
                            {"_id": session_id},
                            {"$set": {
                                "emotion_distribution": emotion_dist,
                                "total_frames_analyzed": frames_processed,
                                "avg_confidence_score": round(data.get("confidence", 0.5), 4),
                            }},
                        )
                    except Exception as save_err:
                        logger.warning(f"[WS] Failed to save metrics: {save_err}")

                await websocket.send_json({"type": "metrics_ack", "frame_count": frames_processed})
                continue

            if msg_type == "frame":
                frame_data = message.get("data")
                if not frame_data:
                    await websocket.send_json({"type": "error", "error": "No frame data provided"})
                    continue

                # Backpressure: drop frames that arrive too fast
                now_ms = time.time() * 1000
                if (now_ms - _last_frame_time) < _MIN_FRAME_INTERVAL_MS:
                    continue  # Skip this frame
                _last_frame_time = now_ms

                # If model not available, guard with AI_SAFE_MODE
                if inference is None or inference.model is None:
                    if not settings.ai_safe_mode:
                        await websocket.send_json({
                            "type": "error",
                            "error": "FER model not loaded (AI_SAFE_MODE=false)",
                        })
                        continue
                    # Safe-mode: still run MediaPipe for real posture/gaze
                    mp_data = {"posture": "Good", "eye_contact": "Center",
                               "head_pose": None, "gaze_ratio": 0.5}
                    if inference is not None and inference.mediapipe_analyzer is not None:
                        try:
                            image = inference.decode_base64_frame(frame_data)
                            mp_data = await asyncio.to_thread(
                                inference.mediapipe_analyzer.analyze, image
                            )
                        except Exception:
                            pass
                    # Track safe-mode emotions too
                    emotion_counts["neutral"] = emotion_counts.get("neutral", 0) + 1

                    await websocket.send_json({
                        "type": "emotion",
                        "data": {
                            "emotion": "neutral",
                            "confidence": 0.5,
                            "posture": mp_data.get("posture", "Good"),
                            "eye_contact": mp_data.get("eye_contact", "Center"),
                            "head_pose": mp_data.get("head_pose"),
                            "gaze_ratio": mp_data.get("gaze_ratio", 0.5),
                            "probabilities": {},
                            "inference_ms": 0,
                            "frame_count": frames_processed,
                        },
                    })
                    frames_processed += 1
                    continue

                try:
                    result = await asyncio.to_thread(
                        inference.predict_from_base64, frame_data
                    )
                except Exception as infer_err:
                    logger.error(f"[WS] Frame inference crashed: {infer_err}")
                    result = {"success": False, "error": str(infer_err)}

                if result.get("success"):
                    frames_processed += 1
                    total_latency += result.get("inference_time_ms", 0)

                    # Track emotion distribution
                    detected_emotion = result.get("emotion", "neutral")
                    emotion_counts[detected_emotion] = emotion_counts.get(detected_emotion, 0) + 1

                    # Persist emotion distribution to DB every 10 frames
                    _emotion_save_counter += 1
                    if _emotion_save_counter >= 10:
                        _emotion_save_counter = 0
                        try:
                            total = sum(emotion_counts.values())
                            emotion_dist = {k: round(v / total, 4) for k, v in emotion_counts.items()}
                            avg_conf = result.get("confidence", 0.5)
                            await db.sessions_collection.update_one(
                                {"_id": session_id},
                                {"$set": {
                                    "emotion_distribution": emotion_dist,
                                    "total_frames_analyzed": frames_processed,
                                    "avg_confidence_score": round(avg_conf, 4),
                                }},
                            )
                        except Exception as save_err:
                            logger.warning(f"[WS] Failed to save emotion data: {save_err}")

                    await websocket.send_json({
                        "type": "emotion",
                        "data": {
                            "emotion": result.get("emotion", "neutral"),
                            "confidence": result.get("confidence", 0.5),
                            "probabilities": result.get("all_probabilities", {}),
                            "inference_ms": result.get("inference_time_ms", 0),
                            "frame_count": frames_processed,
                            "posture": result.get("posture", "Unknown"),
                            "eye_contact": result.get("eye_contact", "Unknown"),
                            "head_pose": result.get("head_pose"),
                            "gaze_ratio": result.get("gaze_ratio"),
                            "multiple_faces": result.get("multiple_faces", False),
                        },
                    })
                else:
                    # Don't crash — just log and continue processing frames
                    error_msg = result.get("error", "Inference failed")
                    if error_msg != "Inference failed":
                        logger.warning(f"[WS] Frame error: {error_msg}")
                    await websocket.send_json({
                        "type": "error",
                        "error": error_msg,
                    })

            elif msg_type == "audio":
                audio_data = message.get("data")
                if not audio_data:
                    continue

                # streaming=True means real-time chunk → skip Whisper (too slow)
                # streaming=False/absent means final recording → full transcription
                is_streaming = message.get("streaming", False)
                transcribe = not is_streaming

                try:
                    audio_service = get_audio_service()
                    result = await asyncio.to_thread(
                        audio_service.analyze_from_base64, audio_data, transcribe
                    )
                    await websocket.send_json({
                        "type": "audio_analysis",
                        "data": result,
                    })
                except Exception as audio_err:
                    logger.error(f"[WS] Audio analysis failed: {audio_err}")
                    # Never let audio errors crash the WebSocket — return graceful failure
                    try:
                        await websocket.send_json({
                            "type": "audio_analysis",
                            "data": {
                                "success": False,
                                "error": str(audio_err),
                                "transcript": None,
                                "clarity": None,
                            },
                        })
                    except Exception:
                        pass  # WebSocket may already be closed

            elif msg_type == "stats":
                avg_latency = total_latency / frames_processed if frames_processed > 0 else 0
                await websocket.send_json({
                    "type": "stats",
                    "data": {
                        "frames_processed": frames_processed,
                        "avg_latency_ms": round(avg_latency, 2),
                    },
                })

    except WebSocketDisconnect:
        manager.disconnect(session_id)
        # Save final emotion distribution on disconnect
        if emotion_counts and db.sessions_collection:
            try:
                total = sum(emotion_counts.values())
                emotion_dist = {k: round(v / total, 4) for k, v in emotion_counts.items()}
                await db.sessions_collection.update_one(
                    {"_id": session_id},
                    {"$set": {
                        "emotion_distribution": emotion_dist,
                        "total_frames_analyzed": frames_processed,
                    }},
                )
            except Exception:
                pass
    except Exception as e:
        print(f"[WS] Error for {session_id}: {e}")
        manager.disconnect(session_id)
        # Save final emotion distribution on error too
        if emotion_counts and db.sessions_collection:
            try:
                total = sum(emotion_counts.values())
                emotion_dist = {k: round(v / total, 4) for k, v in emotion_counts.items()}
                await db.sessions_collection.update_one(
                    {"_id": session_id},
                    {"$set": {
                        "emotion_distribution": emotion_dist,
                        "total_frames_analyzed": frames_processed,
                    }},
                )
            except Exception:
                pass
