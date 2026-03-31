"""API Routers — backed by SQLite.

Routers included eagerly by main.py:
  - auth       POST /auth/signup, /auth/login, /auth/reset-password
  - history    POST /history/save, GET /history/user/{user_id}
  - interview  POST /interview/start_session, /interview/next_question, etc.
  - health     GET /health, /health/inference, /health/gpu

Optional (loaded conditionally):
  - multimodal  WebSocket /multimodal/ws/{session_id}
"""
