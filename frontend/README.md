# Smart AI Interview Assistant - Frontend (MVP)

A lightweight React application for interview practice. Features local video recording and AI-powered feedback submission.

## Features

- **Local Recording**: Uses browser `MediaRecorder` API to capture video/audio locally.
- **REST Integration**: Submits session data to a FastAPI backend.
- **AI Feedback**: Displays structured feedback on content, delivery, and scoring.

## Tech Stack

- React 18
- Vite
- Tailwind CSS

## Prerequisites

- Node.js 18+
- Backend server running on `http://localhost:8000`

## Installation

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

The app will be available at `http://localhost:5173`

## Project Structure

```
frontend/
├── src/
│   ├── components/
│   │   ├── Recorder.jsx       # Video capture component
│   │   └── Feedback.jsx       # Result display component
│   ├── api/
│   │   └── feedback.js        # API client
│   ├── App.jsx                # Main application logic
│   └── main.jsx               # Entry point
├── index.html
├── vite.config.js
└── tailwind.config.js
```

## Browser Requirements

- Chrome / Edge / Firefox / Safari
- Requires camera and microphone permissions.
