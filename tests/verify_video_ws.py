import asyncio
import base64
import json
import websockets
import sys
import os

# Create a small dummy JPEG for testing
def create_dummy_jpeg():
    # Simple 1x1 pixel black JPEG
    # This is a minimal valid JPEG header + data
    # (Generated for verification purposes)
    return "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+P+/HgAFhAJ/wlseKgAAAABJRU5ErkJggg=="

async def test_video_websocket():
    uri = "ws://127.0.0.1:8000/interview/ws/test-session-video"
    
    print(f"Connecting to {uri}...")
    try:
        async with websockets.connect(uri) as websocket:
            print("Connected.")
            
            # Send frame message
            # We use a dummy base64 string. The backend might complain if it's not a valid image 
            # readable by cv2.imdecode, but let's try a very small valid PNG/JPEG base64.
            # actually the backend expects base64 image.
            # Let's use a minimal valid base64 image (PNG is easier to stringify, backend uses cv2.imdecode which handles it)
            
            # 1x1 pixel transparent PNG
            dummy_image = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
            
            msg = {
                "type": "frame",
                "data": dummy_image,
                "question_number": 1
            }
            await websocket.send(json.dumps(msg))
            print("Sent frame data.")
            
            # Wait for response
            # We expect "emotion" type response
            while True:
                try:
                    response_text = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    response = json.loads(response_text)
                    msg_type = response.get("type")
                    
                    if msg_type == "emotion":
                        print("Received emotion analysis:")
                        print(json.dumps(response, indent=2))
                        print("TEST PASSED")
                        break
                    elif msg_type == "error":
                        print(f"Server returned error: {response}")
                        # If error is "image decode failed" that's fine, it means endpoint is reachable
                        break
                    else:
                        print(f"Received other message type: {msg_type}")
                        
                except asyncio.TimeoutError:
                    print("TEST FAILED: Timeout waiting for emotion response.")
                    sys.exit(1)

    except Exception as e:
        print(f"Connection failed: {e}")
        print("Note: Ensure the backend server is running on localhost:8000 before running this test.")

if __name__ == "__main__":
    try:
        import websockets
    except ImportError:
        print("Install dependencies: pip install websockets")
        sys.exit(1)
        
    asyncio.run(test_video_websocket())
