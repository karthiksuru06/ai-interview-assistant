# Smart AI Interview Assistant — Project Brief

## 🚀 Overview
The **Smart AI Interview Assistant** is a state-of-the-art, end-to-end platform designed to help job seekers prepare for interviews using real-time AI feedback. It combines **Facial Emotion Recognition (FER)**, **Voice Analysis**, and **Generative AI (Gemini)** to provide a holistic coaching experience.

---

## 🏗️ Architecture & Tech Stack

### 🔹 Frontend (React + Vite)
- **Core**: React 18, Vite (for ultra-fast development/builds).
- **Styling**: Tailwind CSS for a premium, high-tech "glassmorphism" aesthetic.
- **Animations**: Framer Motion for smooth transitions and interactive HUD elements.
- **Real-time Engine**: Browser-side **MediaPipe** integration for 0ms latency facial tracking (Fast AI mode).
- **Visualization**: Recharts for performance trends and emotion breakdowns.

### 🔹 Backend (FastAPI + Python)
- **Framework**: FastAPI (Asynchronous, high-performance Python web framework).
- **AI Engine**: 
  - **Google Gemini 1.5 Flash**: Orchestrates question generation, adaptive follow-ups, and answer evaluation.
  - **Whisper (OpenAI)**: Handles precise Speech-to-Text (STT) for fluency analysis.
- **VoiceClarityAnalyzer**: Custom DSP logic for Signal-to-Noise (SNR) and consistency tracking.
- **Data Persistence**:
  - **SQLite**: (Default) Lightweight local database for zero-setup demos.
  - **MongoDB Atlas**: (Production) Scalable NoSQL storage for user sessions and history.
- **WebSocket**: Real-time bi-directional communication for audio/video stream analysis.

---

## 🌟 Core Features

### 1. Adaptive AI Interviewer
The system doesn't just ask static questions. It monitors the user's **emotional state** (Happiness, Stress, Neutrality) and **performance scores** to dynamically adjust the difficulty:
- **Stress > 50%**: Eases down to a simpler, confidence-building question.
- **Confidence > 75%**: Ramps up to a deeper, multi-part "challenge" question.

### 2. Multi-Metric HUD (Heads-Up Display)
During the interview, users see real-time metrics for:
- **Facial Confidence (FCS)**: Derived from emotion analysis.
- **Eye Contact (ECS)**: Tracked via gaze deviation.
- **Voice Clarity (VCS)**: Measures SNR and volume consistency.
- **Emotional Stability (ESS)**: Tracks transition rates and emotional variance.
- **Fluency (FS)**: Analyzes Words Per Minute (WPM) and filler word count.

### 3. Comprehensive Performance Reports
After each session, the system generates:
- **IRS (Interview Readiness Score)**: A weighted average of all core metrics.
- **Emotion Breakdown**: Detailed pie chart of the user's emotional journey.
- **AI Recommendations**: Targeted tips for improvement.
- **PDF Export**: Shareable performance reports with full Q&A transcripts.

---

## 🛠️ Recent Improvements (Phase 2)
- ✅ **Expanded Subject Bank**: Added 'Software Engineering', 'Data Science', 'Machine Learning', and 'Product Management'.
- ✅ **Adaptive Logic**: Implemented "Pro AI" (Backend-side model) vs "Fast AI" (Browser-side model) toggle.
- ✅ **Graceful Failures**: Implemented 60s timeouts and "AI thinking" provisional scoring (5/10) to prevent session interruptions.
- ✅ **Security**: Enhanced JWT-based authentication and secure password hashing.

---

## 📂 Project Structure
```text
/backend/
  ├── app/                  # REST API & WebSocket logic
  ├── src/                  # Deep learning models (LSTM/CNN)
  ├── models/               # Pre-trained FER weights (.pth)
  └── test_db.sqlite        # Local storage (fallback)
/frontend/
  ├── src/pages/            # Dashboard, Session, History, Auth
  ├── src/services/         # MediaPipe/FaceAnalyzer logic
  └── src/api/              # Axios configuration & interceptors
/tests/                     # Preflight & integration test suite
```

---

## 🏁 Quality Assurance
The project currently passes **31/31** Preflight Release Checks, ensuring that file structures, PDF engines, database connections, and AI services are ready for deployment.
