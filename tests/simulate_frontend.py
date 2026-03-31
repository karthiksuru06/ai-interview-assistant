import asyncio
import aiohttp
import json
import base64
import random
import os
import sys

# Constants
BASE_URL = "http://127.0.0.1:8000/interview"
WS_URL = "ws://127.0.0.1:8000/interview/ws"

async def simulate_session():
    print(f"🚀 Starting Comprehensive Simulation...")
    
    async with aiohttp.ClientSession() as session:
        # 1. Start Session
        print(f"\n[1] Creating Session...")
        async with session.post(f"{BASE_URL}/start_session", json={
            "user_id": "sim-user",
            "job_role": "React Developer",
            "subject": "React",
            "difficulty": "medium"
        }) as resp:
            if resp.status not in (200, 201):
                print(f"❌ Failed to start session: {resp.status} {await resp.text()}")
                return
            data = await resp.json()
            session_id = data["id"]
            print(f"✅ Session Created: {session_id}")

        # 2. Connect WebSocket
        print(f"\n[2] Connecting WebSocket...")
        ws_endpoint = f"{WS_URL}/{session_id}"
        
        try:
            async with session.ws_connect(ws_endpoint) as ws:
                print(f"✅ WebSocket Connected")
                
                # 3. Simulate Media Flow (Send 5 frames and 5 audio chunks)
                print(f"\n[3] Sending Media Data (Video & Audio)...")
                
                # Generate fake image (black 320x240)
                fake_image = bytes([0] * (320 * 240 * 3)) # Raw RGB? No, backend expects JPEG base64. 
                # Actually, let's just send a minimal valid base64 JPEG header + junk, 
                # or better, just random bytes and expect "inference failed" but WS stays open?
                # The backend attempts `cv2.imdecode`. Random bytes will fail decode.
                # Let's try to send a valid-ish header or just accept generic error response is OK 
                # as long as WS doesn't crash.
                # BETTER: The backend `inference.py` catches 422? NO, `imdecode` returns None.
                # `predict_from_base64` returns `success: False`. This verifies the pipeline!
                
                fake_frame_b64 = base64.b64encode(b"fake_jpeg_data").decode("utf-8")
                
                # Fake WebM audio header (1A 45 DF A3) + junk
                fake_audio_webm = base64.b64encode(b"\x1a\x45\xdf\xa3" + b"\x00"*100).decode("utf-8")
                
                responses_received = {"emotion": 0, "audio_analysis": 0, "error": 0}

                # Send loop
                for i in range(3):
                    # Send Frame
                    await ws.send_json({
                        "type": "frame",
                        "data": fake_frame_b64,
                        "question_number": 1
                    })
                    
                    # Send Audio
                    await ws.send_json({
                        "type": "audio",
                        "data": fake_audio_webm
                    })
                    
                    # Wait for responses
                    try:
                        # We expect at least 2 messages (emotion + audio_analysis)
                        # but might get 'stats' or others. Read a few.
                        read_count = 0
                        while read_count < 3:
                            msg = await asyncio.wait_for(ws.receive(), timeout=2.0)
                            
                            if msg.type == aiohttp.WSMsgType.TEXT:
                                data = json.loads(msg.data)
                                msg_type = data.get("type")
                                print(f"   Received: {msg_type} -> Success: {data.get('data', {}).get('success', 'N/A')}")
                                
                                if msg_type == "emotion":
                                    d = data.get("data", {})
                                    if "posture" in d and "eye_contact" in d:
                                        print(f"     ✅ Analytics found: Posture={d['posture']}, Eye={d['eye_contact']}")
                                    else:
                                        print(f"     ❌ Analytics MISSING!")
                                    responses_received["emotion"] += 1
                                    
                                elif msg_type == "audio_analysis":
                                    d = data.get("data", {})
                                    print(f"     ✅ Transcribe Result: {d.get('transcript') or 'None (Expected)'}")
                                    responses_received["audio_analysis"] += 1
                                    
                                elif msg_type == "error":
                                    responses_received["error"] += 1
                                    print(f"     ⚠️ Backend Error: {data.get('error')}")

                                read_count += 1
                                # Break if we got what we wanted for this iteration
                                if responses_received["emotion"] >= i+1 and responses_received["audio_analysis"] >= i+1:
                                    break
                            
                            elif msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                                print("❌ WebSocket Closed Unexpectedly")
                                break
                                
                    except asyncio.TimeoutError:
                        print("   ⏳ Receive timeout (moving to next send)")
                        pass

                print(f"✅ Media Simulation Complete. Stats: {responses_received}")

        except Exception as e:
            print(f"❌ WebSocket Failed: {e}")
            return

        # 4. Next Question
        print(f"\n[4] Advancing Question...")
        async with session.get(f"{BASE_URL}/next_question?session_id={session_id}&current_question_id=1") as resp:
            if resp.status == 200:
                q_data = await resp.json()
                print(f"✅ Next Question Fetched: Q{q_data.get('question_number')}")
            else:
                print(f"⚠️ Next Question Warning: {resp.status} (Might be end of list)")

        # 5. End Session
        print(f"\n[5] Ending Session...")
        async with session.post(f"{BASE_URL}/end_session", json={
            "session_id": session_id,
            "total_duration": 120
        }) as resp:
            if resp.status == 200:
                summary = await resp.json()
                print(f"✅ Session Ended. Summary Keys: {list(summary.keys())}")
                if "overall_score" in summary:
                    print(f"   Final Score: {summary['overall_score']}")
            else:
                print(f"❌ End Session Failed: {resp.status}")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(simulate_session())
