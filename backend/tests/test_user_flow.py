"""
User Journey Validation Script
===============================
Validates the COMPLETE client-facing browser flow end-to-end.

Run modes:
  1. AUTOMATED (Playwright)  — pip install playwright && playwright install
     python -m pytest tests/test_user_flow.py -v

  2. API-ONLY (no browser)   — validates backend contracts match frontend expectations
     python -m pytest tests/test_user_flow.py -v -k "api"

  3. MANUAL CHECKLIST         — printed to stdout
     python tests/test_user_flow.py --checklist

Flow under test:
  Step 1:  Open http://localhost:5173
  Step 2:  Verify redirect to /login  (ProtectedRoute guard)
  Step 3:  Enter email + password → Login → redirect to /dashboard
  Step 4:  Select "Software Engineering" + "Hard" → Click "Start Interview"
  Step 5:  Verify camera permission prompt and "AI Online" badge appears
  Step 6:  Wait 10 seconds → Click "End Session" → redirect to /history
"""

import sys
import time
import asyncio
import logging
from datetime import datetime

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

FRONTEND_URL = "http://localhost:5173"
BACKEND_URL = "http://localhost:8000"

# Test credentials (works in Dev Mode with USE_MONGODB=false)
TEST_EMAIL = "test@example.com"
TEST_PASSWORD = "any-password-works"

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
#  SECTION A — API-Level Validation  (no browser needed)
# ═══════════════════════════════════════════════════════════════════════════

class TestAPIUserFlow:
    """
    Validates that backend API contracts match what the frontend expects.
    Run: python -m pytest tests/test_user_flow.py -v -k "api"
    """

    @staticmethod
    def _get_client():
        import httpx
        return httpx.Client(base_url=BACKEND_URL, timeout=10)

    # ── Step 1: Health Check ──────────────────────────────────────────────

    def test_api_01_backend_is_running(self):
        """Backend health endpoint responds."""
        client = self._get_client()
        resp = client.get("/health")
        assert resp.status_code == 200, f"Health check failed: {resp.status_code}"
        data = resp.json()
        assert "status" in data
        print(f"  [PASS] Backend running: {data}")

    # ── Step 2: Login (Dev Mode — Magic Login) ───────────────────────────

    def test_api_02_login_returns_jwt(self):
        """
        POST /auth/login with JSON {email, password} returns
        {access_token, token_type, role} — matching frontend's expectations.
        """
        client = self._get_client()
        resp = client.post("/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD,
        })
        assert resp.status_code == 200, f"Login failed: {resp.status_code} — {resp.text}"
        data = resp.json()

        assert "access_token" in data, "Missing access_token in login response"
        assert "role" in data, "Missing role in login response"
        assert data["token_type"] == "bearer"
        print(f"  [PASS] Login OK — role={data['role']}, token_length={len(data['access_token'])}")
        return data["access_token"]

    # ── Step 3: Start Interview Session ───────────────────────────────────

    def test_api_03_start_session_with_subject_and_difficulty(self):
        """
        POST /interview/start_session with {user_id, job_role, subject, difficulty}
        returns {id, status: 'created'} — proving Dashboard → Backend link works.
        """
        client = self._get_client()

        # Login first
        login_resp = client.post("/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD,
        })
        token = login_resp.json()["access_token"]

        # Start session with the EXACT payload InterviewSession.jsx sends
        resp = client.post(
            "/interview/start_session",
            json={
                "user_id": "test-user-001",
                "job_role": "Software Engineering",
                "subject": "software-engineering",
                "difficulty": "hard",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 201, f"Start session failed: {resp.status_code} — {resp.text}"
        data = resp.json()

        assert "id" in data, "Missing session id"
        assert data["subject"] == "software-engineering"
        assert data["difficulty"] == "hard"
        assert data["status"] == "created"
        print(f"  [PASS] Session created — id={data['id']}, subject={data['subject']}, difficulty={data['difficulty']}")
        return data["id"]

    # ── Step 4: End Session ───────────────────────────────────────────────

    def test_api_04_end_session(self):
        """
        POST /interview/session/{id}/end returns summary data.
        """
        client = self._get_client()

        login_resp = client.post("/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD,
        })
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Create session
        create_resp = client.post("/interview/start_session", json={
            "user_id": "test-user-001",
            "job_role": "Software Engineering",
            "subject": "software-engineering",
            "difficulty": "hard",
        }, headers=headers)
        session_id = create_resp.json()["id"]

        # End it
        resp = client.post(f"/interview/session/{session_id}/end", headers=headers)
        assert resp.status_code == 200, f"End session failed: {resp.status_code} — {resp.text}"
        data = resp.json()

        assert "session_id" in data
        assert "total_questions" in data
        print(f"  [PASS] Session ended — {data}")

    # ── Step 5: History Retrieval ─────────────────────────────────────────

    def test_api_05_history_returns_past_sessions(self):
        """
        GET /history/user/{user_id} returns list of past sessions
        after at least one session has been created.
        """
        client = self._get_client()

        login_resp = client.post("/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD,
        })
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Create and end a session to ensure history exists
        create_resp = client.post("/interview/start_session", json={
            "user_id": "test-user-001",
            "job_role": "Data Science",
            "subject": "data-science",
            "difficulty": "medium",
        }, headers=headers)
        session_id = create_resp.json()["id"]
        client.post(f"/interview/session/{session_id}/end", headers=headers)

        # Now fetch history
        resp = client.get("/history/user/test-user-001", headers=headers)
        assert resp.status_code == 200, f"History fetch failed: {resp.status_code} — {resp.text}"
        data = resp.json()

        assert isinstance(data, list), "History should return a list"
        assert len(data) > 0, "History should have at least 1 session"
        print(f"  [PASS] History contains {len(data)} session(s)")

    # ── Step 6: Full Flow Sequence ────────────────────────────────────────

    def test_api_06_full_flow_sequence(self):
        """
        Complete user journey via API:
        Login → Start Session (subject+difficulty) → End Session → Fetch History
        """
        client = self._get_client()

        # 1. Login
        login_resp = client.post("/auth/login", json={
            "email": "fullflow@test.com",
            "password": "doesnt-matter",
        })
        assert login_resp.status_code == 200
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print("  [1/4] Login ...................... OK")

        # 2. Start Session with subject + difficulty
        start_resp = client.post("/interview/start_session", json={
            "user_id": "test-user-001",
            "job_role": "Machine Learning",
            "subject": "machine-learning",
            "difficulty": "hard",
        }, headers=headers)
        assert start_resp.status_code == 201
        session_id = start_resp.json()["id"]
        assert start_resp.json()["subject"] == "machine-learning"
        assert start_resp.json()["difficulty"] == "hard"
        print(f"  [2/4] Start Session .............. OK (id={session_id})")

        # 3. End Session
        end_resp = client.post(f"/interview/session/{session_id}/end", headers=headers)
        assert end_resp.status_code == 200
        print(f"  [3/4] End Session ................ OK")

        # 4. Fetch History
        history_resp = client.get("/history/user/test-user-001", headers=headers)
        assert history_resp.status_code == 200
        sessions = history_resp.json()
        assert len(sessions) >= 1
        print(f"  [4/4] History .................... OK ({len(sessions)} sessions)")

        print("\n  ✓ FULL API FLOW PASSED")


# ═══════════════════════════════════════════════════════════════════════════
#  SECTION B — Browser Automation  (Playwright)
# ═══════════════════════════════════════════════════════════════════════════

class TestBrowserUserFlow:
    """
    Full browser-level Playwright tests simulating a real user.

    Requirements:
      pip install playwright pytest-playwright
      playwright install chromium

    Run:
      python -m pytest tests/test_user_flow.py::TestBrowserUserFlow -v --headed
    """

    @staticmethod
    def _launch():
        """Helper to check if playwright is available."""
        try:
            from playwright.sync_api import sync_playwright
            return True
        except ImportError:
            return False

    def test_browser_01_redirect_to_login(self, page):
        """Step 1-2: Opening root URL redirects to /login."""
        page.goto(FRONTEND_URL)
        page.wait_for_url("**/login", timeout=5000)
        assert "/login" in page.url
        print(f"  [PASS] Redirected to: {page.url}")

    def test_browser_02_login_to_dashboard(self, page):
        """Step 3: Enter credentials → Login → Redirect to /dashboard."""
        page.goto(f"{FRONTEND_URL}/login")
        page.wait_for_load_state("networkidle")

        # Fill in the login form
        page.fill('input[type="email"]', TEST_EMAIL)
        page.fill('input[type="password"]', TEST_PASSWORD)

        # Click sign in
        page.click('button[type="submit"]')

        # Should redirect to dashboard
        page.wait_for_url("**/dashboard", timeout=10000)
        assert "/dashboard" in page.url
        print(f"  [PASS] Logged in, redirected to: {page.url}")

    def test_browser_03_select_subject_and_start(self, page):
        """Step 4: Select subject + difficulty → Start → /session page loads."""
        # Login first
        page.goto(f"{FRONTEND_URL}/login")
        page.fill('input[type="email"]', TEST_EMAIL)
        page.fill('input[type="password"]', TEST_PASSWORD)
        page.click('button[type="submit"]')
        page.wait_for_url("**/dashboard", timeout=10000)

        # Click "Software Engineering" subject card
        page.click('text=Software Engineering')

        # Click "Hard" difficulty
        page.click('text=Hard')

        # Click "Start Interview Session"
        page.click('text=Start Interview Session')

        # Should navigate to /session
        page.wait_for_url("**/session", timeout=5000)
        assert "/session" in page.url

        # Verify subject badge is displayed
        assert page.locator('text=Software Engineering').is_visible()
        assert page.locator('text=Hard').is_visible()
        print(f"  [PASS] Session started with correct subject and difficulty")

    def test_browser_04_camera_and_ai_badge(self, page):
        """Step 5: Verify AI Online badge appears on session page."""
        # Login → Dashboard → Start Session
        page.goto(f"{FRONTEND_URL}/login")
        page.fill('input[type="email"]', TEST_EMAIL)
        page.fill('input[type="password"]', TEST_PASSWORD)
        page.click('button[type="submit"]')
        page.wait_for_url("**/dashboard", timeout=10000)

        page.click('text=Software Engineering')
        page.click('text=Hard')
        page.click('text=Start Interview Session')
        page.wait_for_url("**/session", timeout=5000)

        # Grant camera permissions (Playwright handles this via browser context)
        # Check for AI Online badge
        ai_badge = page.locator('text=AI Online')
        assert ai_badge.is_visible(timeout=5000)
        print(f"  [PASS] AI Online badge is visible")

    def test_browser_05_end_session_to_history(self, page):
        """Step 6: Wait → End Session → Redirect to /history."""
        # Login → Dashboard → Start Session
        page.goto(f"{FRONTEND_URL}/login")
        page.fill('input[type="email"]', TEST_EMAIL)
        page.fill('input[type="password"]', TEST_PASSWORD)
        page.click('button[type="submit"]')
        page.wait_for_url("**/dashboard", timeout=10000)

        page.click('text=General Interview')
        page.click('text=Medium')
        page.click('text=Start Interview Session')
        page.wait_for_url("**/session", timeout=5000)

        # Wait 10 seconds as specified in requirements
        page.wait_for_timeout(10000)

        # Click "End Session"
        page.click('text=End Session')

        # Should redirect to /history
        page.wait_for_url("**/history", timeout=10000)
        assert "/history" in page.url

        # Verify history page loaded
        assert page.locator('text=Interview History').is_visible()
        print(f"  [PASS] Session ended, redirected to history: {page.url}")


# ═══════════════════════════════════════════════════════════════════════════
#  SECTION C — Manual Checklist (Printable)
# ═══════════════════════════════════════════════════════════════════════════

MANUAL_CHECKLIST = """
╔══════════════════════════════════════════════════════════════════════════╗
║        SMART AI INTERVIEW ASSISTANT — USER JOURNEY CHECKLIST           ║
║                       Manual QA Verification                            ║
╠══════════════════════════════════════════════════════════════════════════╣
║                                                                          ║
║  Prerequisites:                                                          ║
║  □ Backend running:  cd backend && python run.py                        ║
║  □ Frontend running: cd frontend && npm run dev                         ║
║  □ .env has:         USE_MONGODB=false                                  ║
║                                                                          ║
╠══════════════════════════════════════════════════════════════════════════╣
║                                                                          ║
║  STEP 1: SECURITY REDIRECT                                              ║
║  ─────────────────────────────────────────────────────                   ║
║  □ Open http://localhost:5173 in browser                                ║
║  □ VERIFY: Automatically redirected to /login                           ║
║  □ VERIFY: Login form visible with email + password fields              ║
║                                                                          ║
║  STEP 2: LOGIN (DEV MODE)                                               ║
║  ─────────────────────────────────────────────────────                   ║
║  □ Enter email:    test@example.com                                     ║
║  □ Enter password: anything                                             ║
║  □ Click "Sign In"                                                      ║
║  □ VERIFY: Redirected to /dashboard                                     ║
║  □ VERIFY: "Welcome, test@example.com" shows in navbar                  ║
║                                                                          ║
║  STEP 3: SUBJECT & DIFFICULTY SELECTION                                  ║
║  ─────────────────────────────────────────────────────                   ║
║  □ VERIFY: 6 subject cards displayed                                    ║
║  □ Click "Software Engineering" card                                    ║
║  □ VERIFY: Card border turns purple (selected)                          ║
║  □ Click "Hard" difficulty                                              ║
║  □ VERIFY: Summary shows "Software Engineering" + "Hard" badges         ║
║  □ Click "Start Interview Session" button                               ║
║  □ VERIFY: Redirected to /session                                       ║
║                                                                          ║
║  STEP 4: INTERVIEW SESSION                                               ║
║  ─────────────────────────────────────────────────────                   ║
║  □ VERIFY: Browser asks for camera/mic permission → Allow               ║
║  □ VERIFY: Live camera feed visible on left side                        ║
║  □ VERIFY: "AI Online" green badge in top-left of video                 ║
║  □ VERIFY: "AI Coach" tip box at bottom of video                        ║
║  □ VERIFY: "Software Engineering" badge in navbar                       ║
║  □ VERIFY: "Hard" badge in navbar                                       ║
║  □ VERIFY: Right sidebar shows real-time analytics:                     ║
║            - Interview Readiness Score                                   ║
║            - Confidence Over Time chart                                  ║
║            - Performance Metrics radar chart                             ║
║            - Key Metrics (Fluency, Eye Contact, Content, Tone, Pacing)  ║
║  □ VERIFY: Console shows "[Session] Created: <id>"                      ║
║  □ Wait 10 seconds                                                      ║
║  □ VERIFY: Metrics update every ~3 seconds                              ║
║                                                                          ║
║  STEP 5: END SESSION                                                     ║
║  ─────────────────────────────────────────────────────                   ║
║  □ Click "End Session" (red button)                                     ║
║  □ VERIFY: Redirected to /history                                       ║
║  □ VERIFY: "Interview History" page title visible                       ║
║  □ VERIFY: At least one past session card displayed                     ║
║  □ VERIFY: Session card shows subject, difficulty, and date             ║
║                                                                          ║
║  STEP 6: NAVIGATION                                                     ║
║  ─────────────────────────────────────────────────────                   ║
║  □ Click "Back to Dashboard"                                            ║
║  □ VERIFY: Returns to /dashboard                                        ║
║  □ Can start a new session with different subject/difficulty             ║
║                                                                          ║
╠══════════════════════════════════════════════════════════════════════════╣
║                                                                          ║
║  EDGE CASES:                                                             ║
║  □ Refresh page while on /dashboard → stays authenticated               ║
║  □ Navigate directly to /session without login → redirected to /login   ║
║  □ Logout → token cleared → all protected routes redirect to /login     ║
║                                                                          ║
╚══════════════════════════════════════════════════════════════════════════╝
"""

if __name__ == "__main__":
    if "--checklist" in sys.argv:
        print(MANUAL_CHECKLIST)
    else:
        print("Usage:")
        print("  Automated (API):     python -m pytest tests/test_user_flow.py -v -k 'api'")
        print("  Automated (Browser): python -m pytest tests/test_user_flow.py -v -k 'browser' --headed")
        print("  Manual Checklist:    python tests/test_user_flow.py --checklist")
