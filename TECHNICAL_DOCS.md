# Technical Documentation

> Smart AI Interview Assistant — Architecture, API Reference, and Folder Structure.

---

## 1. System Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                        CLIENT (Browser)                          │
│  React 18 + Vite 5 + Tailwind CSS                               │
│  ┌────────────┐  ┌──────────────┐  ┌──────────────────────────┐ │
│  │ Auth Pages │  │  Dashboard   │  │  Interview Session       │ │
│  │ Login      │  │ Subject Pick │  │  Camera + WebSocket      │ │
│  │ Signup     │  │ Difficulty   │  │  TTS + Silence Detection │ │
│  │ ForgotPwd  │  │ Start Btn   │  │  Live Transcript         │ │
│  └────────────┘  └──────────────┘  └──────────────────────────┘ │
│           │              │                    │                   │
│           └──────────────┼────────────────────┘                  │
│                     Axios + WebSocket                            │
└────────────────────────┬─────────────────────────────────────────┘
                         │ HTTP :8000 / WS :8000
┌────────────────────────┴─────────────────────────────────────────┐
│                     BACKEND (FastAPI)                             │
│  ┌─────────┐  ┌──────────────┐  ┌────────────┐  ┌────────────┐ │
│  │  Auth   │  │  Interview   │  │  History   │  │  Health    │ │
│  │ Router  │  │  Router      │  │  Router    │  │  Router    │ │
│  └────┬────┘  └──────┬───────┘  └─────┬──────┘  └─────┬──────┘ │
│       │              │                │                │         │
│  ┌────┴──────────────┴────────────────┴────────────────┴──────┐ │
│  │                    SERVICES LAYER                          │ │
│  │  gemini.py   inference.py   audio.py   metrics.py         │ │
│  │  fusion.py   pressure.py   audio_inference.py             │ │
│  └────┬──────────────┬────────────────┬───────────────────────┘ │
│       │              │                │                          │
│  ┌────┴────┐   ┌─────┴─────┐   ┌─────┴──────┐                 │
│  │ MongoDB │   │ PyTorch   │   │ Gemini API │                  │
│  │ (Motor) │   │ GPU/CPU   │   │ (Google)   │                  │
│  └─────────┘   └───────────┘   └────────────┘                  │
└──────────────────────────────────────────────────────────────────┘
```

---

## 2. API Reference

### 2.1 Authentication

| Method | Endpoint | Body | Response |
|--------|----------|------|----------|
| `POST` | `/auth/signup` | `{email, username, password, security_question, security_answer}` | `{id, email, username, token}` |
| `POST` | `/auth/login` | `{email, password}` | `{token, user: {id, email, username, role}}` |
| `POST` | `/auth/reset-password` | `{email, security_answer, new_password}` | `{message}` |

### 2.2 Interview Session

| Method | Endpoint | Body | Response |
|--------|----------|------|----------|
| `POST` | `/interview/start_session` | `{user_id, job_role, subject, difficulty}` | `{id, status: "created"}` |
| `POST` | `/interview/next_question` | `{session_id, previous_answer?, emotion_context?, metrics_context?}` | `{question_number, question_text, question_type, tips?}` |
| `POST` | `/interview/submit_answer` | `{session_id, question_number, answer_text, duration_seconds?}` | `{score, feedback, strengths[], improvements[], golden_answer?, follow_up_suggested}` |
| `POST` | `/interview/session/{id}/end` | — | `{session_id, duration_minutes, total_questions, performance_rating, recommendations[]}` |
| `GET`  | `/interview/session/{id}` | — | Full session document |

### 2.3 Frame Analysis

| Method | Endpoint | Body | Response |
|--------|----------|------|----------|
| `POST` | `/interview/analyze_frame` | `{frame_base64}` | `{success, emotion: {emotion, confidence, all_probabilities, inference_time_ms}}` |

### 2.4 WebSocket Protocol

**Endpoint:** `ws://localhost:8000/interview/ws/{session_id}`

| Client Message | Server Response | Description |
|---|---|---|
| `{"type": "frame", "data": "<base64>"}` | `{"type": "emotion", "data": {emotion, confidence, probabilities, inference_ms, posture, eye_contact}}` | Send video frame for emotion analysis |
| `{"type": "silence"}` | `{"type": "silence", "metrics": 0}` | Silence gate — skips GPU inference |
| `{"type": "ping"}` | `{"type": "pong"}` | Keep-alive heartbeat |
| `{"type": "stats"}` | `{"type": "stats", "data": {frames_processed, avg_latency_ms}}` | Get inference statistics |

### 2.5 History

| Method | Endpoint | Response |
|--------|----------|----------|
| `GET` | `/history/user/{user_id}` | `[{id, job_role, subject, difficulty, overall_score, created_at, completed_at, ...}]` |

### 2.6 Health

| Method | Endpoint | Response |
|--------|----------|----------|
| `GET` | `/health` | `{status, version, gpu_available, gpu_name, model_loaded, database_connected}` |
| `GET` | `/health/inference` | `{model_loaded, device, model_architecture, warm, total_inferences, avg_inference_time_ms}` |
| `GET` | `/health/gpu` | `{available, device_name, cuda_version, total_memory_gb, ...}` |

---

## 3. Folder Structure

```
ai interview project/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                 # FastAPI app factory, CORS, lifecycle
│   │   ├── config.py               # Pydantic Settings (env vars)
│   │   ├── database.py             # Hybrid MongoDB / SQLite / Mock
│   │   ├── models.py               # Data models
│   │   ├── schemas.py              # Pydantic request/response schemas
│   │   ├── routers/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py             # Signup, Login, Password Reset
│   │   │   ├── interview.py        # Session CRUD, Q&A, WebSocket
│   │   │   ├── history.py          # Session history retrieval
│   │   │   ├── health.py           # System health checks
│   │   │   ├── feedback.py         # Feedback endpoints
│   │   │   └── multimodal.py       # Real-time video+audio fusion
│   │   └── services/
│   │       ├── __init__.py
│   │       ├── inference.py         # FER model (EfficientNet-B0, PyTorch)
│   │       ├── gemini.py            # Google Gemini AI integration
│   │       ├── audio.py             # Voice clarity analysis
│   │       ├── audio_inference.py   # Audio model inference
│   │       ├── metrics.py           # 5-metric IRS calculator
│   │       ├── fusion.py            # Multimodal result fusion
│   │       └── pressure.py          # Adaptive difficulty engine
│   ├── models/
│   │   └── best_model.pth          # Trained FER weights
│   ├── tests/
│   │   ├── test_api.py             # API endpoint tests
│   │   └── final_verify.py         # Health check script
│   ├── docs/
│   │   └── SYSTEM_ARCHITECTURE.md
│   ├── requirements.txt
│   ├── run.py                      # Uvicorn launcher
│   ├── Dockerfile
│   └── .env                        # Environment configuration
│
├── frontend/
│   ├── src/
│   │   ├── App.jsx                 # Routes + AuthProvider
│   │   ├── main.jsx                # React entry point
│   │   ├── index.css               # Global styles + Tailwind
│   │   ├── context/
│   │   │   └── AuthContext.jsx     # JWT auth state management
│   │   ├── api/
│   │   │   └── axios.js           # Axios instance + interceptors
│   │   ├── pages/
│   │   │   ├── Auth/
│   │   │   │   ├── Login.jsx
│   │   │   │   ├── Signup.jsx
│   │   │   │   └── ForgotPassword.jsx
│   │   │   ├── Dashboard.jsx       # Subject + difficulty selector
│   │   │   ├── InterviewSession.jsx # Live interview (camera, WS, TTS)
│   │   │   ├── History.jsx         # Past sessions + PDF export
│   │   │   ├── QuestionBank.jsx    # Curated Q&A reference
│   │   │   └── Admin.jsx           # Admin dashboard
│   │   └── components/
│   │       ├── ProtectedRoute.jsx  # Route guards (auth + admin)
│   │       ├── LiveSession.jsx     # Camera feed component
│   │       └── Recorder.jsx        # Video recording
│   ├── package.json
│   ├── vite.config.js
│   ├── tailwind.config.js
│   ├── postcss.config.js
│   └── Dockerfile
│
├── docker-compose.yml              # Multi-container orchestration
├── README.md                       # Quick start guide
├── USER_GUIDE.md                   # Non-technical user guide
├── TECHNICAL_DOCS.md               # This file
├── VIVA_SUPPORT.md                 # 10 hard viva Q&A
└── HANDOVER.md                     # Project handover notes
```

---

## 4. Key Design Decisions

### 4.1 Hybrid Database (MongoDB / SQLite)
A single `USE_MONGODB` toggle in `.env` switches between production MongoDB and local SQLite. The `SQLiteCollection` class mirrors Motor's async API, so routers require zero code changes.

### 4.2 Silence Gate (WebSocket)
When the frontend detects silence (audio RMS < 0.01) or the mic is muted, it sends `{"type": "silence"}` instead of a video frame. The backend responds instantly without invoking the CNN, saving GPU cycles and reducing latency.

### 4.3 AI Safe Mode
`AI_SAFE_MODE=true` enables mock responses when the FER model or Gemini API is unavailable. This allows the full UI flow to work for demos and testing. In production (`false`), all AI must produce real results.

### 4.4 Adaptive Question Difficulty
The Gemini prompt includes the previous answer's score. Scores below 5/10 trigger easier follow-ups; scores above 8/10 escalate difficulty. Emotion context (e.g., "nervous") also softens question selection.

### 4.5 Session Comparison
When submitting answers or ending sessions, the system fetches the user's most recent completed session and generates a comparison text (e.g., "User improved by 2.3 points"). This is fed into Gemini's evaluation prompt for contextual feedback.

---

## 5. Environment Variables

| Variable | Default | Description |
|---|---|---|
| `USE_MONGODB` | `true` | `true` = MongoDB Atlas, `false` = SQLite |
| `MONGODB_URL` | `mongodb+srv://localhost:27017/interview_db` | MongoDB connection string |
| `GEMINI_API_KEY` | — | Google Gemini API key (required) |
| `GEMINI_MODEL` | `gemini-2.5-flash` | Gemini model name |
| `JWT_SECRET_KEY` | `your-super-secret-key...` | JWT signing secret |
| `JWT_ALGORITHM` | `HS256` | JWT algorithm |
| `JWT_EXPIRE_MINUTES` | `1440` | Token lifetime (24h) |
| `AI_SAFE_MODE` | `false` | Allow mock AI responses |
| `FER_MODEL_PATH` | `./models/best_model.pth` | Path to FER model weights |
| `INFERENCE_DEVICE` | `cuda` | `cuda` or `cpu` |
| `HOST` | `0.0.0.0` | Server bind address |
| `PORT` | `8000` | Server bind port |

---

## 6. Technology Stack

| Component | Technology | Version |
|---|---|---|
| Backend Framework | FastAPI | 0.109+ |
| ASGI Server | Uvicorn | 0.27+ |
| Database (Prod) | MongoDB Atlas + Motor | Motor 3.3+ |
| Database (Dev) | SQLite + aiosqlite | 0.19+ |
| AI Model | PyTorch + EfficientNet-B0 | PyTorch 2.1+ |
| Question AI | Google Gemini | 2.5 Flash |
| Speech-to-Text | OpenAI Whisper | Latest |
| Body Analysis | MediaPipe | 0.10.9+ |
| Frontend | React | 18.2 |
| Build Tool | Vite | 5.0+ |
| CSS | Tailwind CSS | 3.4+ |
| Animation | Framer Motion | 12+ |
| Charts | Recharts | 2.10+ |
| PDF Export | jsPDF + jspdf-autotable | 4.1+ / 5.0+ |
| Auth | python-jose + passlib + bcrypt | JWT HS256 |
| Containerisation | Docker + Docker Compose | 3.8 |
