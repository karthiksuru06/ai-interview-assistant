import asyncio
import aiohttp
import websockets
import json
import base64
import sys

# Configuration
BASE_URL = "http://127.0.0.1:8000"
WS_URL = "ws://127.0.0.1:8000/interview/ws"

async def test_full_flow():
    print(f"Testing full flow against {BASE_URL}...")

    async with aiohttp.ClientSession() as session:
        # 1. Start Session
        print("\n[1] Starting Session...")
        try:
            async with session.post(f"{BASE_URL}/interview/start_session", json={
                "user_id": "test_user_verify",
                "job_role": "Software Engineer",
                "subject": "React",
                "difficulty": "medium"
            }) as resp:
                if resp.status not in (200, 201):
                    text = await resp.text()
                    print(f"❌ Start Session failed: {resp.status} {text}")
                    return
                data = await resp.json()
                session_id = data["id"]
                print(f"✅ Session Started. ID: {session_id}")
        except Exception as e:
            print(f"❌ Failed to connect to API: {e}")
            return

        # 2. WebSocket Connection
        print("\n[2] Connecting WebSocket...")
        ws_endpoint = f"{WS_URL}/{session_id}"
        print(f"Connecting to {ws_endpoint}")
        
        try:
            async with websockets.connect(ws_endpoint) as ws:
                print("✅ WebSocket Connected!")

                # 3. Send Frame
                print("\n[3] Sending Dummy Frame...")
                # 1x1 pixel JPEG base64
                dummy_frame = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKwITAAAAABJRU5ErkJggg=="
                
                await ws.send(json.dumps({
                    "type": "frame",
                    "data": dummy_frame,
                    "question_number": 1
                }))
                
                # Wait for response
                try:
                    response = await asyncio.wait_for(ws.recv(), timeout=5.0)
                    print(f"✅ Received WS Response: {response}")
                except asyncio.TimeoutError:
                    print("❌ WS Response Timeout")

                # 4. Send Audio (Silence)
                print("\n[4] Sending Silence...")
                await ws.send(json.dumps({"type": "silence"}))
                response = await asyncio.wait_for(ws.recv(), timeout=5.0)
                print(f"✅ Received Silence Response: {response}")
                
        except Exception as e:
            print(f"❌ WebSocket Failed: {e}")

        # 5. Next Question
        print("\n[5] Fetching Next Question...")
        async with session.post(f"{BASE_URL}/interview/next_question", json={
            "session_id": session_id,
            "previous_answer": "I know React hooks.",
            "emotion_context": {"neutral": 0.9}
        }) as resp:
            if resp.status == 200:
                q_data = await resp.json()
                print(f"✅ Next Question: {q_data.get('question_text')}")
            else:
                 print(f"❌ Next Question Failed: {resp.status}")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(test_full_flow())
