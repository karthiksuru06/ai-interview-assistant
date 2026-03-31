# Viva Support — 10 Hard Questions & Answers

> Prepared answers for project defence / viva voce examination.

---

### Q1. Why did you choose FastAPI over Flask or Django?

**Answer:** FastAPI was chosen for three critical reasons:
1. **Native async support** — Our WebSocket endpoint streams video frames at ~5 FPS. FastAPI's ASGI architecture handles thousands of concurrent WebSocket connections without blocking, unlike Flask's WSGI.
2. **Automatic OpenAPI documentation** — Every endpoint generates interactive Swagger docs at `/docs`, which was essential for frontend-backend parallel development.
3. **Pydantic integration** — Request/response schemas are validated at runtime with zero boilerplate. Our `SessionCreate`, `AnswerSubmit`, and `QuestionResponse` schemas catch malformed data before it reaches business logic.

---

### Q2. How does the Facial Emotion Recognition (FER) model work?

**Answer:** We use an **EfficientNet-B0** convolutional neural network fine-tuned on the FER2013+ dataset to classify 8 emotions: neutral, happiness, surprise, sadness, anger, disgust, fear, and contempt.

**Pipeline:**
1. Frontend captures a video frame via `getUserMedia()` and encodes it as base64.
2. The frame is sent over WebSocket to `interview/ws/{session_id}`.
3. Backend decodes the base64 string, resizes to 224x224, normalises pixel values, and passes through the CNN.
4. Softmax output gives probability distribution across all 8 classes.
5. The top emotion + confidence score is returned to the frontend in under 50ms on GPU.

The model weights are stored at `backend/models/best_model.pth` and loaded once at server startup to avoid repeated disk I/O.

---

### Q3. Explain the WebSocket protocol used for real-time analysis.

**Answer:** The WebSocket endpoint at `/interview/ws/{session_id}` uses a typed JSON message protocol:

| Client Sends | Server Responds | Purpose |
|---|---|---|
| `{"type": "frame", "data": "<base64>"}` | `{"type": "emotion", "data": {...}}` | Video frame analysis |
| `{"type": "silence"}` | `{"type": "silence", "metrics": 0}` | Silence gate — skips GPU inference |
| `{"type": "ping"}` | `{"type": "pong"}` | Keep-alive heartbeat |
| `{"type": "stats"}` | `{"type": "stats", "data": {...}}` | Inference statistics |

The **silence gate** is a performance optimisation: when the frontend detects the microphone is muted or audio RMS falls below 0.01, it sends `"silence"` instead of frame data. The backend returns immediately without invoking the CNN, saving GPU cycles.

---

### Q4. How does the AI generate adaptive interview questions?

**Answer:** We use **Google Gemini 2.5 Flash** with a structured prompt that includes:
- Job role and subject domain
- Difficulty level (easy / medium / hard)
- All previously asked questions (to prevent repetition)
- The candidate's last answer + its score (for adaptive difficulty)
- Current emotion context (e.g., "candidate appears nervous")
- Real-time metrics context (confidence, eye contact scores)

If the previous answer scored below 5/10, Gemini generates an easier follow-up. If above 8/10, it escalates difficulty. This creates a personalised, adaptive interview experience.

The prompt also instructs Gemini to return a JSON object with `question_text`, `question_type`, `question_number`, and optional `tips`.

---

### Q5. What is the database architecture and why the hybrid approach?

**Answer:** We implemented a **hybrid database system** controlled by a single toggle: `USE_MONGODB` in `.env`.

- **`USE_MONGODB=true`** (Production): MongoDB Atlas via the Motor async driver. Documents store user profiles and interview sessions with nested question arrays.
- **`USE_MONGODB=false`** (Development/Testing): SQLite with a custom `SQLiteCollection` class that exposes the same async API (`find_one`, `insert_one`, `update_one`, `find().sort().to_list()`) as Motor.

This means **zero code changes** are needed to switch between databases. The same router code works identically against both backends. The SQLite mode also supports a "Magic Login" where any email/password combination works, enabling rapid testing without credential management.

Fallback chain in MongoDB mode: Configured Atlas URL → Local MongoDB (localhost:27017) → JSON file mock.

---

### Q6. How does JWT authentication work in this system?

**Answer:** Authentication uses a stateless JWT token flow:

1. **Signup:** Password is hashed with `passlib[bcrypt]` using `CryptContext(schemes=["bcrypt"])`. The hash, email, username, and a security question/answer are stored in the users collection.
2. **Login:** The submitted password is verified against the stored hash. On success, a JWT token is created using `python-jose` with the payload `{"sub": user_id, "role": "user|admin", "exp": now + 24h}`, signed with `HS256`.
3. **Frontend storage:** The token is stored in `localStorage`. The `AuthContext` decodes it client-side to extract user ID, role, and username.
4. **API requests:** An Axios interceptor attaches `Authorization: Bearer <token>` to every request. The backend validates the token on protected endpoints.
5. **Password reset:** Uses the security question/answer stored at signup — no email service required.

---

### Q7. How do you handle the 5-metric Interview Readiness Score (IRS)?

**Answer:** The IRS is a weighted composite score calculated from five independent metrics:

| Metric | Weight | Source | How It's Measured |
|---|---|---|---|
| Facial Confidence | 20% | EfficientNet-B0 CNN | Confidence probability of positive emotions |
| Eye Contact | 15% | MediaPipe Face Mesh | Gaze ratio from iris landmark tracking |
| Voice Clarity | 20% | Web Audio API + Whisper | Signal-to-noise ratio + amplitude analysis |
| Emotional Stability | 25% | Emotion variance tracker | Standard deviation of emotion scores over time |
| Fluency | 20% | Speech rate analysis | Words-per-minute + filler word count |

The metrics service (`services/metrics.py`) collects frame-by-frame data, computes rolling averages, and produces the final IRS. The frontend displays this as a real-time animated bar and radar chart.

---

### Q8. What happens when the AI services (Gemini/GPU) are unavailable?

**Answer:** The system has a configurable **AI Safe Mode** (`AI_SAFE_MODE` in `.env`):

- **`AI_SAFE_MODE=true`**: All AI components fall back to mock/placeholder responses. The FER model returns `"neutral"` with 50% confidence. Gemini returns pre-written fallback questions and generic feedback. This allows the full UI flow to work for demos without GPU or API keys.
- **`AI_SAFE_MODE=false`**: No mocks are allowed. If the FER model isn't loaded, the WebSocket returns an explicit error. If Gemini fails, the endpoint returns an HTTP 500. This is the production setting that ensures all scores are genuine.

The inference service also gracefully handles model loading failure at startup — it logs a warning but doesn't crash the server, allowing non-AI endpoints (auth, history) to continue working.

---

### Q9. Explain the silence detection and Text-to-Speech (TTS) features.

**Answer:**

**Silence Detection** (Frontend → Backend):
1. The frontend creates an `AudioContext` and `AnalyserNode` from the user's microphone stream.
2. Every animation frame, it computes the **Root Mean Square (RMS)** of the audio buffer: `RMS = sqrt(mean(samples²))`.
3. If RMS falls below a threshold of `0.01`, the `isSilent` state is set to `true`.
4. When silent (or mic is muted), the WebSocket sends `{"type": "silence"}` instead of video frame data.
5. The backend's **Silence Gate** responds immediately with `{"type": "silence", "metrics": 0}` — no CNN inference, no GPU cost.

**Text-to-Speech** (Frontend):
1. When a new question arrives from the backend, a `useEffect` hook triggers `window.speechSynthesis`.
2. A `SpeechSynthesisUtterance` is created with the question text at 0.95x speed.
3. The user can toggle TTS on/off with a button. When disabled, `speechSynthesis.cancel()` stops any in-progress speech.

---

### Q10. How would you scale this system for 1000 concurrent users?

**Answer:** Current bottlenecks and solutions:

1. **WebSocket connections**: FastAPI + Uvicorn handles ~10K concurrent WebSockets per worker. Deploy with `uvicorn --workers 4` behind an NGINX reverse proxy with `proxy_pass` for WebSocket upgrade.

2. **GPU inference**: The FER model runs on a single GPU. For scale:
   - Use **TorchServe** or **Triton Inference Server** to batch requests.
   - Deploy multiple GPU pods via Kubernetes with a load balancer.
   - Reduce frame rate from 5 FPS to 2 FPS per client (still adequate for emotion tracking).

3. **MongoDB**: Atlas auto-scales with connection pooling. Add read replicas for history queries. Shard the sessions collection by `user_id`.

4. **Gemini API**: Rate-limited by Google. Implement a request queue with exponential backoff. Cache common questions per (subject, difficulty) to reduce API calls.

5. **Frontend**: Already a static SPA. Serve via CDN (CloudFront / Vercel). WebSocket connections go directly to the backend cluster.

Architecture: `CDN → NGINX → K8s (FastAPI workers) → GPU pool + MongoDB Atlas + Gemini API`
