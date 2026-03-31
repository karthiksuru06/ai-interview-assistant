"""
Multimodal WebSocket Router
===========================
Real-time video + audio fusion endpoint for interview analysis.
Includes dynamic question generation and pressure-based difficulty adjustment.
"""

import asyncio
import json
import time
from datetime import datetime
from typing import Dict, Optional, List

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.inference import get_inference_service
from app.services.audio_inference import get_audio_inference_service
from app.services.fusion import get_fusion_service, FusionResult
from app.services.metrics import get_metrics_calculator
from app.services.pressure import get_pressure_manager, clear_pressure_manager
from app.services.gemini import get_gemini_service

router = APIRouter(prefix="/multimodal", tags=["Multimodal"])


class MultimodalConnectionManager:
    """Manage multimodal WebSocket connections."""

    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.session_stats: Dict[str, Dict] = {}
        self.session_questions: Dict[str, List[str]] = {}  # Track asked questions per session
        self.session_qa_history: Dict[str, List[Dict]] = {}  # Q&A history for session summary

    async def connect(self, websocket: WebSocket, session_id: str):
        await websocket.accept()
        self.active_connections[session_id] = websocket
        self.session_stats[session_id] = {
            "connected_at": time.time(),
            "frames_processed": 0,
            "audio_chunks_processed": 0,
            "total_latency_ms": 0,
            "question_count": 0,
            "current_question": None,
            "question_start_time": None,
        }
        self.session_questions[session_id] = []
        self.session_qa_history[session_id] = []

    def disconnect(self, session_id: str):
        self.active_connections.pop(session_id, None)
        stats = self.session_stats.pop(session_id, None)
        self.session_questions.pop(session_id, None)
        self.session_qa_history.pop(session_id, None)
        if stats:
            duration = time.time() - stats["connected_at"]
            print(f"[WS] Session {session_id} ended. Duration: {duration:.1f}s, "
                  f"Frames: {stats['frames_processed']}, Questions: {stats['question_count']}")

    async def send_json(self, session_id: str, data: dict):
        if session_id in self.active_connections:
            await self.active_connections[session_id].send_json(data)

    def update_stats(self, session_id: str, latency_ms: float, has_video: bool, has_audio: bool):
        if session_id in self.session_stats:
            stats = self.session_stats[session_id]
            if has_video:
                stats["frames_processed"] += 1
            if has_audio:
                stats["audio_chunks_processed"] += 1
            stats["total_latency_ms"] += latency_ms


manager = MultimodalConnectionManager()


@router.websocket("/ws/{session_id}")
async def multimodal_websocket(websocket: WebSocket, session_id: str):
    """
    Real-time multimodal analysis WebSocket endpoint.

    Accepts JSON payloads with video frames and/or audio chunks,
    runs parallel inference, fuses results, and returns unified feedback.

    Client Message Format:
    {
        "type": "analyze",
        "video_frame": "<base64_encoded_image>",  // Optional
        "audio_chunk": "<base64_encoded_audio>",  // Optional
        "question_number": 1,                      // Optional
        "timestamp": 1706000000000                 // Client timestamp
    }

    Server Response Format:
    {
        "type": "analysis",
        "data": {
            "current_emotion": "happiness",
            "confidence_score": 0.82,
            "confidence_level": "excellent",
            "video_emotion": "happiness",
            "audio_emotion": "neutral",
            "modality_agreement": false,
            "nervous_cues": [],
            "feedback_tip": "Great composure! Keep it up.",
            "metrics": {
                "facial_confidence": 85.2,
                "voice_clarity": 78.5,
                "emotional_stability": 82.1
            },
            "latency_ms": 45.2
        }
    }
    """
    await manager.connect(websocket, session_id)

    # Get services
    video_service = get_inference_service()
    audio_service = get_audio_inference_service()
    fusion_service = get_fusion_service()
    metrics_calc = get_metrics_calculator(session_id)
    gemini_service = get_gemini_service()

    # Session tracking
    frame_count = 0
    total_latency = 0.0
    job_role = "software-engineer"  # Will be updated from client
    difficulty = "medium"  # Will be updated from client
    pressure_manager = None  # Initialized on first question request

    try:
        while True:
            # Receive message
            raw_data = await websocket.receive_text()
            start_time = time.perf_counter()

            try:
                message = json.loads(raw_data)
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "error": "Invalid JSON format"
                })
                continue

            msg_type = message.get("type", "")

            # Handle ping/pong for keepalive
            if msg_type == "ping":
                await websocket.send_json({
                    "type": "pong",
                    "timestamp": time.time()
                })
                continue

            # Handle analysis request
            if msg_type == "analyze":
                video_frame = message.get("video_frame")
                audio_chunk = message.get("audio_chunk")
                question_number = message.get("question_number")

                # Run inference in parallel
                video_result = None
                audio_result = None

                try:
                    # Process video frame
                    if video_frame and video_service.model is not None:
                        video_result = video_service.predict_from_base64(video_frame)

                    # Process audio chunk
                    if audio_chunk and audio_service.model is not None:
                        audio_result = audio_service.predict_from_base64(audio_chunk)

                    # Fuse results
                    fusion_result = fusion_service.fuse(
                        session_id=session_id,
                        video_result=video_result,
                        audio_result=audio_result
                    )

                    # Update metrics calculator
                    if video_result and video_result.get("success"):
                        metrics_calc.process_video_frame(
                            emotion_probs=video_result.get("all_probabilities", {}),
                            gaze_deviation=0.1,  # Placeholder - integrate gaze tracker
                            is_looking_at_camera=True
                        )

                    # Update pressure manager with emotion
                    if pressure_manager and fusion_result.fused_emotion:
                        pressure_manager.update_emotion(
                            emotion=fusion_result.fused_emotion,
                            confidence=fusion_result.confidence_score
                        )

                    # Calculate total latency
                    total_processing_time = (time.perf_counter() - start_time) * 1000

                    # Get current metrics
                    current_metrics = metrics_calc.get_current_metrics()

                    # Build response
                    response = {
                        "type": "analysis",
                        "data": {
                            # Primary results
                            "current_emotion": fusion_result.fused_emotion,
                            "confidence_score": fusion_result.confidence_score,
                            "confidence_level": fusion_result.confidence_level.value,

                            # Component analysis
                            "video_emotion": fusion_result.video_emotion,
                            "video_confidence": fusion_result.video_confidence,
                            "audio_emotion": fusion_result.audio_emotion,
                            "audio_confidence": fusion_result.audio_confidence,

                            # Agreement analysis
                            "modality_agreement": fusion_result.modality_agreement,
                            "nervous_cues_detected": fusion_result.nervous_cues_detected,
                            "nervous_cues": fusion_result.nervous_cues,

                            # Feedback
                            "feedback_tip": fusion_result.feedback_tip,
                            "detailed_feedback": fusion_result.detailed_feedback,

                            # Metrics
                            "metrics": current_metrics.get("metrics", {}),
                            "irs": current_metrics.get("irs", {}).get("irs", 0),

                            # Performance
                            "latency_ms": round(total_processing_time, 2),
                            "frame_number": frame_count,
                            "timestamp": time.time(),

                            # Pressure (if available)
                            "pressure": {
                                "level": pressure_manager.pressure_level,
                                "zone": pressure_manager.get_current_zone().value,
                                "difficulty": pressure_manager.get_current_difficulty().value,
                            } if pressure_manager else None
                        }
                    }

                    await websocket.send_json(response)

                    # Update stats
                    frame_count += 1
                    total_latency += total_processing_time
                    manager.update_stats(
                        session_id, total_processing_time,
                        video_frame is not None, audio_chunk is not None
                    )

                except Exception as frame_err:
                    print(f"[WS] Error processing frame: {frame_err}")
                    # Don't close connection, just log and continue
                    continue

            # Handle get_question request
            elif msg_type == "get_question":
                try:
                    # Extract session config if provided
                    job_role = message.get("job_role", job_role)
                    difficulty = message.get("difficulty", difficulty)

                    # Initialize pressure manager if not exists
                    if pressure_manager is None:
                        pressure_manager = get_pressure_manager(session_id, difficulty)

                    # Get current emotion context from fusion service
                    session_summary = fusion_service.get_session_summary(session_id)
                    emotion_context = session_summary.get("emotion_distribution", {})

                    # Get pressure-adjusted difficulty
                    current_difficulty = pressure_manager.get_current_difficulty().value

                    # Update question count
                    stats = manager.session_stats.get(session_id, {})
                    stats["question_count"] = stats.get("question_count", 0) + 1
                    question_number = stats["question_count"]

                    # Get previous questions and last answer
                    previous_questions = manager.session_questions.get(session_id, [])
                    previous_answer = None
                    qa_history = manager.session_qa_history.get(session_id, [])
                    if qa_history:
                        previous_answer = qa_history[-1].get("answer")

                    # Generate question using Gemini
                    question_data = await gemini_service.generate_question(
                        job_role=job_role,
                        difficulty=current_difficulty,
                        question_number=question_number,
                        previous_questions=previous_questions,
                        previous_answer=previous_answer,
                        emotion_context=emotion_context
                    )

                    # Store question
                    question_text = question_data.get("question_text", "")
                    manager.session_questions[session_id].append(question_text)
                    stats["current_question"] = question_text
                    stats["question_start_time"] = time.time()

                    # Get pressure state
                    pressure_state = pressure_manager.get_state()

                    await websocket.send_json({
                        "type": "question",
                        "data": {
                            "question_number": question_number,
                            "question": question_text,
                            "question_type": question_data.get("question_type", "behavioral"),
                            "tips": question_data.get("tips", []),
                            "difficulty": current_difficulty,
                            "pressure": {
                                "level": pressure_state.pressure_level,
                                "zone": pressure_state.zone.value,
                                "feedback": pressure_state.feedback,
                                "tips": pressure_state.tips,
                                "emotion_component": pressure_state.emotion_component,
                                "performance_component": pressure_state.performance_component,
                            }
                        }
                    })

                except Exception as q_err:
                    print(f"[WS] Error generating question: {q_err}")
                    await websocket.send_json({
                        "type": "error",
                        "error": f"Failed to generate question: {str(q_err)}"
                    })

            # Handle submit_answer request
            elif msg_type == "submit_answer":
                try:
                    answer = message.get("answer", "")
                    response_time = message.get("response_time")  # Optional: client-provided time

                    stats = manager.session_stats.get(session_id, {})
                    current_question = stats.get("current_question", "")
                    question_start = stats.get("question_start_time")

                    # Calculate response time if not provided
                    if response_time is None and question_start:
                        response_time = time.time() - question_start

                    # Get emotion context during response
                    session_summary = fusion_service.get_session_summary(session_id)
                    emotion_data = {
                        "dominant_emotion": session_summary.get("dominant_emotion", "neutral"),
                        "avg_confidence": session_summary.get("avg_confidence", 0.5),
                    }

                    # Evaluate answer using Gemini
                    evaluation = await gemini_service.evaluate_answer(
                        question=current_question,
                        answer=answer,
                        job_role=job_role,
                        emotion_data=emotion_data
                    )

                    # Store Q&A in history
                    qa_entry = {
                        "question": current_question,
                        "answer": answer,
                        "score": evaluation.get("score", 5),
                        "feedback": evaluation.get("feedback", ""),
                        "response_time": response_time,
                    }
                    manager.session_qa_history[session_id].append(qa_entry)

                    # Update pressure manager with performance
                    if pressure_manager:
                        pressure_manager.update_performance(
                            answer_score=evaluation.get("score"),
                            response_time_seconds=response_time
                        )
                        pressure_state = pressure_manager.get_state()
                    else:
                        pressure_state = None

                    await websocket.send_json({
                        "type": "answer_feedback",
                        "data": {
                            "score": evaluation.get("score", 5),
                            "feedback": evaluation.get("feedback", ""),
                            "strengths": evaluation.get("strengths", []),
                            "improvements": evaluation.get("improvements", []),
                            "follow_up_suggested": evaluation.get("follow_up_suggested", False),
                            "response_time": response_time,
                            "pressure": {
                                "level": pressure_state.pressure_level if pressure_state else 50,
                                "zone": pressure_state.zone.value if pressure_state else "growth",
                                "difficulty": pressure_state.difficulty.value if pressure_state else "medium",
                                "feedback": pressure_state.feedback if pressure_state else "",
                                "tips": pressure_state.tips if pressure_state else [],
                            } if pressure_state else None
                        }
                    })

                except Exception as a_err:
                    print(f"[WS] Error evaluating answer: {a_err}")
                    await websocket.send_json({
                        "type": "error",
                        "error": f"Failed to evaluate answer: {str(a_err)}"
                    })

            # Handle get_pressure request
            elif msg_type == "get_pressure":
                if pressure_manager:
                    pressure_state = pressure_manager.get_state()
                    pressure_stats = pressure_manager.get_stats()
                    await websocket.send_json({
                        "type": "pressure_state",
                        "data": {
                            "level": pressure_state.pressure_level,
                            "zone": pressure_state.zone.value,
                            "difficulty": pressure_state.difficulty.value,
                            "emotion_component": pressure_state.emotion_component,
                            "performance_component": pressure_state.performance_component,
                            "feedback": pressure_state.feedback,
                            "tips": pressure_state.tips,
                            "stats": pressure_stats,
                        }
                    })
                else:
                    await websocket.send_json({
                        "type": "pressure_state",
                        "data": None
                    })

            # Handle stats request
            elif msg_type == "stats":
                avg_latency = total_latency / max(1, frame_count)
                session_summary = fusion_service.get_session_summary(session_id)

                await websocket.send_json({
                    "type": "stats",
                    "data": {
                        "frames_processed": frame_count,
                        "avg_latency_ms": round(avg_latency, 2),
                        "session_summary": session_summary,
                        "video_service_status": video_service.get_status(),
                        "audio_service_status": audio_service.get_status()
                    }
                })

            # Handle session end
            elif msg_type == "end_session":
                summary = fusion_service.get_session_summary(session_id)
                metrics_summary = metrics_calc.get_session_summary()
                qa_history = manager.session_qa_history.get(session_id, [])
                pressure_stats = pressure_manager.get_stats() if pressure_manager else None

                # Generate session summary using Gemini if we have Q&A history
                ai_summary = None
                if qa_history:
                    try:
                        ai_summary = await gemini_service.generate_session_summary(
                            job_role=job_role,
                            questions_and_answers=qa_history,
                            overall_emotion_data=summary
                        )
                    except Exception as sum_err:
                        print(f"[WS] Error generating AI summary: {sum_err}")

                await websocket.send_json({
                    "type": "session_complete",
                    "data": {
                        "fusion_summary": summary,
                        "metrics_summary": metrics_summary,
                        "total_frames": frame_count,
                        "avg_latency_ms": round(total_latency / max(1, frame_count), 2),
                        "questions_answered": len(qa_history),
                        "qa_history": qa_history,
                        "pressure_stats": pressure_stats,
                        "ai_summary": ai_summary,
                    }
                })

                # Cleanup
                fusion_service.clear_session(session_id)
                clear_pressure_manager(session_id)
                break

    except WebSocketDisconnect:
        manager.disconnect(session_id)
        fusion_service.clear_session(session_id)
        clear_pressure_manager(session_id)
        print(f"[WS] Client {session_id} disconnected")

    except Exception as e:
        print(f"[WS] Error for {session_id}: {e}")
        manager.disconnect(session_id)
        fusion_service.clear_session(session_id)
        clear_pressure_manager(session_id)


@router.get("/session/{session_id}/summary")
async def get_session_summary(session_id: str):
    """Get fusion summary for a session."""
    fusion_service = get_fusion_service()
    return fusion_service.get_session_summary(session_id)
