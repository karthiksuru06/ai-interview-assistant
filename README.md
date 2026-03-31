# Smart AI Interview Assistant

> Real-time multimodal AI-powered mock interview platform with live video analysis, dynamic question generation, and performance tracking.

![Python 3.10+](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-009688?logo=fastapi&logoColor=white)
![React 18](https://img.shields.io/badge/React-18.2-61DAFB?logo=react&logoColor=black)
![MongoDB](https://img.shields.io/badge/MongoDB-Atlas-47A248?logo=mongodb&logoColor=white)
![PyTorch](https://img.shields.io/badge/PyTorch-2.1+-EE4C2C?logo=pytorch&logoColor=white)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)

---

## Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Frontend** | React 18, Vite 5, Tailwind CSS | UI, WebRTC capture, real-time charts |
| **Backend** | FastAPI, Uvicorn, WebSockets | REST API, real-time streaming, orchestration |
| **Database** | MongoDB Atlas (prod) / SQLite (test) | User accounts, session history |
| **Video AI** | PyTorch, EfficientNet-B0 (CNN) | Facial Emotion Recognition (8 classes) |
| **Audio AI** | OpenAI Whisper, Custom LSTM pipeline | Speech-to-text, voice clarity analysis |
| **Question AI** | Google Gemini 2.5 Flash | Dynamic question generation & answer evaluation |
| **Auth** | JWT (python-jose) + pbkdf2_sha256 | Stateless token authentication |

---

## Features

### Real-Time AI Analysis
- **Facial Emotion Recognition** — Live CNN inference (EfficientNet-B0) detecting 8 emotions: neutral, happiness, surprise, sadness, anger, disgust, fear, contempt
- **Voice Clarity Scoring** — Audio SNR analysis, filler word detection, words-per-minute tracking
- **Multimodal Fusion** — Combined video + audio metrics processed in parallel via WebSocket

### Smart Interview Engine
- **Dynamic Question Generation** — Gemini AI generates subject-specific questions across 6 domains (Software Engineering, HR, Data Science, Product Management, Machine Learning, General)
- **Adaptive Difficulty** — Emotion-aware question selection (easier if nervous, harder if confident)
- **AI Answer Evaluation** — Scores 0-10 with feedback, strengths, improvement areas, and follow-up suggestions

### 5-Metric Performance Scoring
| Metric | Weight | Source |
|--------|--------|--------|
| Facial Confidence Score | 20% | CNN emotion analysis |
| Eye Contact Score | 15% | MediaPipe Face Mesh |
| Voice Clarity Score | 20% | Audio SNR + amplitude |
| Emotional Stability Score | 25% | Emotion variance tracking |
| Fluency Score | 20% | Speech rate + filler detection |

Combined into an **Interview Readiness Score (IRS)** displayed in real-time.

### User Features
- **JWT Authentication** — Secure signup/login with security question recovery
- **Interview History** — Browse past sessions with scores, subjects, and difficulty levels
- **Live Dashboard** — Real-time confidence chart, radar metrics, AI coaching tips
- **Admin Panel** — Platform-wide statistics, user management, session analytics

---

## Project Structure

```
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI entry point
│   │   ├── config.py               # Settings + USE_MONGODB toggle
│   │   ├── database.py             # Hybrid MongoDB/SQLite connection
│   │   ├── models.py               # Pydantic data models
│   │   ├── schemas.py              # Request/response schemas
│   │   ├── routers/
│   │   │   ├── auth.py             # Login, Signup, Password Reset
│   │   │   ├── interview.py        # Session management, Q&A, WebSocket
│   │   │   ├── history.py          # Interview history retrieval
│   │   │   ├── health.py           # System health checks
│   │   │   └── multimodal.py       # Real-time video+audio WebSocket
│   │   └── services/
│   │       ├── inference.py         # FER model (EfficientNet-B0, PyTorch)
│   │       ├── gemini.py            # Google Gemini AI integration
│   │       ├── audio.py             # Voice clarity + silence detection
│   │       ├── metrics.py           # 5-metric IRS calculator
│   │       ├── fusion.py            # Multimodal result fusion
│   │       └── pressure.py          # Adaptive difficulty engine
│   ├── tests/
│   │   ├── test_api.py             # API endpoint tests
│   │   ├── final_verify.py         # Runtime health check
│   │   └── preflight_check.py      # Master verification (all features)
│   ├── requirements.txt
│   ├── run.py                       # Uvicorn server launcher
│   └── .env                         # Environment configuration
│
├── frontend/
│   ├── src/
│   │   ├── App.jsx                  # Routes + auth guards
│   │   ├── context/AuthContext.jsx   # JWT auth state management
│   │   ├── api/axios.js             # API client with interceptors
│   │   ├── pages/
│   │   │   ├── Auth/Login.jsx       # Login page
│   │   │   ├── Auth/Signup.jsx      # Registration page
│   │   │   ├── Auth/ForgotPassword.jsx
│   │   │   ├── Dashboard.jsx        # Subject + difficulty selection
│   │   │   ├── InterviewSession.jsx # Live interview (TTS, silence, transcript)
│   │   │   ├── History.jsx          # Past sessions + PDF export
│   │   │   ├── QuestionBank.jsx     # Curated Q&A reference
│   │   │   └── Admin.jsx            # Admin dashboard
│   │   └── components/
│   │       └── ProtectedRoute.jsx   # Route guards (auth + admin)
│   ├── package.json
│   └── vite.config.js
│
├── docker-compose.yml               # MongoDB + Backend + Frontend
├── README.md                        # This file
├── USER_GUIDE.md                    # Non-technical user guide
├── TECHNICAL_DOCS.md                # Architecture & API reference
├── VIVA_SUPPORT.md                  # 10 hard viva Q&A
└── HANDOVER.md                      # Project handover notes
```

---

## How to Run This Project

### Prerequisites

- **Browser:** Chrome or Edge (camera + microphone permissions required)
- **Gemini API Key:** Get one from [Google AI Studio](https://aistudio.google.com/apikey)

---

### Option A: The Docker Way (Recommended - 🚀 Foolproof)

> **IMPORTANT:** This is the most reliable way to run the project. One command spins up MongoDB, the AI Backend, and the React Frontend with all matching dependencies.

**Requirements:** Docker & Docker Compose installed and running.

```bash
# 1. Set your Gemini API key (Required for AI features)
# Windows PowerShell:
$env:GEMINI_API_KEY="your-gemini-api-key-here"
# macOS / Linux:
export GEMINI_API_KEY=your-gemini-api-key-here

# 2. Build and start all services in detached mode
docker-compose up --build -d

# 3. Access the Platform
# Frontend Console: http://localhost:5173
# API Backend: http://localhost:8000
# Swagger Docs: http://localhost:8000/docs
```

> **Tip:** If the frontend shows a blank page initially, give it 30-60 seconds to finish the initial `npm install` inside the container. You can check logs with `docker logs -f interview-frontend`.

**No GPU?** If you don't have an NVIDIA GPU, comment out the `deploy.resources` section in `docker-compose.yml` and set `INFERENCE_DEVICE=cpu`.

**To stop:**
```bash
docker-compose down
```

**To stop and wipe data:**
```bash
docker-compose down -v
```

> **No GPU?** Comment out the `deploy.resources` block in `docker-compose.yml` and set `INFERENCE_DEVICE=cpu`.

---

### Option B: The Manual Way (Undockerized)

> Use this mode if Docker fails or for active development with hot-reload.

**Requirements:** Python 3.10+, Node.js 18+.

**Terminal 1 — Backend:**
```bash
cd backend

# Create and activate virtual environment
python -m venv venv

# Windows:
.\venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# (Optional) GPU support for RTX 4060 / CUDA 12.1:
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121

# Start the server
python run.py
```

**Terminal 2 — Frontend:**
```bash
cd frontend

# Install dependencies
npm install

# Start dev server
npm run dev
```

**Terminal 3 — Verify everything works:**
```bash
python tests/preflight_check.py
```

| Service | URL |
|---------|-----|
| Frontend | http://localhost:5173 |
| Backend API | http://localhost:8000 |
| Swagger Docs | http://localhost:8000/docs |

> **Tip:** Set `USE_MONGODB=false` in `backend/.env` for instant SQLite mode — no MongoDB setup needed. Any email + password will work for login.

---

## Configuration

### The `USE_MONGODB` Toggle

The single most important setting lives in `backend/.env`, line 7:

```env
USE_MONGODB=false    # Test Mode  (SQLite + Magic Login)
USE_MONGODB=true     # Client Mode (MongoDB Atlas + Real Auth)
```

| | Test Mode (`false`) | Client Mode (`true`) |
|---|---|---|
| **Database** | SQLite local file (`test_db.sqlite`) | MongoDB Atlas (cloud) |
| **Login** | Any email + any password works instantly | Real email + password verification |
| **Use Case** | Development, demos, testing AI features | Production, client presentations |
| **Setup Required** | None — works out of the box | MongoDB Atlas URI in `MONGODB_URL` |

**To switch modes:** Change the one line in `backend/.env`, then restart the backend.

### Other Key Settings

```env
# Google Gemini AI (required for question generation)
GEMINI_API_KEY=your-api-key-here
GEMINI_MODEL=gemini-2.5-flash

# JWT Token (change for production)
JWT_SECRET_KEY=change-me-to-a-real-secret-in-production
JWT_EXPIRE_MINUTES=1440          # 24 hours

# AI Safe Mode (fallback to mock responses when AI unavailable)
AI_SAFE_MODE=false               # true = allow mocks, false = require real AI

# MongoDB Atlas (only needed when USE_MONGODB=true)
MONGODB_URL=mongodb+srv://user:pass@cluster.mongodb.net/interview_db
```

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/auth/login` | Authenticate user, return JWT |
| `POST` | `/auth/signup` | Register new user |
| `POST` | `/auth/reset-password` | Reset via security question |
| `POST` | `/interview/start_session` | Create interview session |
| `POST` | `/interview/next_question` | Get AI-generated question |
| `POST` | `/interview/submit_answer` | Submit answer for AI evaluation |
| `POST` | `/interview/session/{id}/end` | End session, generate summary |
| `GET`  | `/history/user/{user_id}` | Get past interview sessions |
| `GET`  | `/health` | System health check |
| `WS`   | `/interview/ws/{session_id}` | Real-time frame analysis |

Full interactive docs: **http://localhost:8000/docs**

---

## User Flow

```
Login ──> Dashboard ──> Select Subject & Difficulty ──> Start Interview
                                                            │
            History  <── End Session <── Live Camera + AI Analytics
```

1. **Login** — Enter any email/password (Test Mode) or real credentials (Client Mode)
2. **Dashboard** — Pick from 6 interview subjects + 3 difficulty levels
3. **Interview** — Live camera feed with real-time AI coaching, emotion tracking, and performance metrics
4. **End Session** — AI generates a comprehensive summary
5. **History** — Review all past sessions with scores and trends

---

## Documentation

| Document | Description |
|----------|-------------|
| [USER_GUIDE.md](USER_GUIDE.md) | Step-by-step guide for non-technical users |
| [TECHNICAL_DOCS.md](TECHNICAL_DOCS.md) | Architecture, API reference, folder structure |
| [VIVA_SUPPORT.md](VIVA_SUPPORT.md) | 10 hard viva questions with prepared answers |
| [HANDOVER.md](HANDOVER.md) | Project handover notes |

---

## License

MIT License — See [LICENSE](LICENSE) for details.
