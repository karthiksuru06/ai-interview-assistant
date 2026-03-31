import pytest
import uuid
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_check():
    """Verify system health endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    # Depending on GPU availability in the test env, 'gpu' might be true or false
    # We just check the key exists
    assert "status" in data
    assert "gpu" in data
    assert data["status"] == "healthy"

def test_start_session():
    """Verify session creation."""
    payload = {
        "job_role": "Python Developer",
        "difficulty": "hard"
    }
    response = client.post("/interview/start_session", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "session_id" in data
    assert "status" in data
    assert data["status"] == "created"

def test_websocket_connection():
    """Verify WebSocket connection and basic inference response."""
    # 1. Create a session first
    start_res = client.post("/interview/start_session", json={"job_role": "Tester"})
    session_id = start_res.json()["session_id"]
    
    # 2. Connect via WebSocket
    # TestClient has a websocket_connect context manager
    with client.websocket_connect(f"/interview/ws/{session_id}") as websocket:
        # Send dummy image data (base64)
        # 1x1 pixel PNG base64
        dummy_image = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
        
        websocket.send_text(dummy_image)
        
        # Receive response
        data = websocket.receive_json()
        
        # Assertions
        assert "emotion" in data
        assert "confidence" in data
        assert "audio_emotion" in data # If multimodal is active
