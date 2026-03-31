import asyncio
import aiohttp
import json
import base64

BASE_URL = "http://127.0.0.1:8000/interview"
WS_URL = "ws://127.0.0.1:8000/interview/ws"

async def verify_analytics():
    print("TEST: Verifying Analytics Response...")
    async with aiohttp.ClientSession() as session:
        # Start Session
        async with session.post(f"{BASE_URL}/start_session", json={
            "user_id": "analytics-test",
            "job_role": "Tester",
            "subject": "Testing", 
            "difficulty": "medium"
        }) as resp:
            data = await resp.json()
            session_id = data["id"]
        
        # Connect WS
        async with session.ws_connect(f"{WS_URL}/{session_id}") as ws:
            # Send fake frame
            await ws.send_json({
                "type": "frame",
                "data": base64.b64encode(b"fake_jpeg").decode("utf-8"),
                "question_number": 1
            })
            
            # Wait for response
            try:
                msg = await ws.receive()
                if msg.type == aiohttp.WSMsgType.TEXT:
                    data = json.loads(msg.data)
                    print(f"RECEIVED: {data}")
                    
                    if data.get("type") == "emotion":
                         payload = data.get("data", {})
                         if "posture" in payload and "eye_contact" in payload:
                             print("✅ SUCCESS: Posture and Eye Contact fields present.")
                         else:
                             print(f"❌ FAILURE: Missing fields. Got: {list(payload.keys())}")
                    elif data.get("type") == "error":
                        # Even an error might contain the default fields if I fixed the mock/fallback correctly
                        # actually, error response usually just has 'error'.
                        # But wait, my fix in interview.py was for the 'safe mode' mock OR the 'inference failed' path?
                        # No, I fixed the 'safe mode' path and I added default args to the inference 'success=True' path.
                        # If inference fails (invalid image), it sends type: error.
                        # I need to know if the backend is running safe mode or real mode.
                        print(f"⚠️ Received Error: {data}")
            except Exception as e:
                print(f"❌ Error receiving: {e}")

if __name__ == "__main__":
    import sys
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(verify_analytics())
