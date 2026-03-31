#!/usr/bin/env python3
"""
Final Verification Script — Smart AI Interview Assistant
=========================================================
Pre-flight health check that validates all critical subsystems
before a demo or deployment.

Usage:
    python tests/final_verify.py

Checks performed:
    1. Backend HTTP health endpoint
    2. MongoDB / database connectivity
    3. ffmpeg availability (for audio processing)
    4. JWT login simulation
    5. Interview session lifecycle
"""

import json
import os
import shutil
import subprocess
import sys
import time

# Allow running from project root or tests/ directory
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

# ── Colours for terminal output ─────────────────────────────────
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"

results = []


def log_pass(label: str, detail: str = ""):
    msg = f"  {GREEN}PASS{RESET}  {label}"
    if detail:
        msg += f"  ({detail})"
    print(msg)
    results.append(("PASS", label))


def log_fail(label: str, detail: str = ""):
    msg = f"  {RED}FAIL{RESET}  {label}"
    if detail:
        msg += f"  — {detail}"
    print(msg)
    results.append(("FAIL", label))


def log_warn(label: str, detail: str = ""):
    msg = f"  {YELLOW}WARN{RESET}  {label}"
    if detail:
        msg += f"  — {detail}"
    print(msg)
    results.append(("WARN", label))


def log_section(title: str):
    print(f"\n{CYAN}{BOLD}[{title}]{RESET}")


# ═══════════════════════════════════════════════════════════════════
#  CHECK 1: Backend Health Endpoint
# ═══════════════════════════════════════════════════════════════════

def check_backend_health():
    log_section("1. Backend Health Check")
    try:
        import requests
    except ImportError:
        # Fall back to urllib if requests not installed
        import urllib.request
        try:
            with urllib.request.urlopen(f"{BACKEND_URL}/health", timeout=10) as resp:
                data = json.loads(resp.read().decode())
                status = data.get("status", "unknown")
                if status == "healthy":
                    log_pass("Backend /health", f"status={status}")
                else:
                    log_warn("Backend /health", f"status={status} (degraded)")
                return data
        except Exception as e:
            log_fail("Backend /health", str(e))
            return None

    try:
        resp = requests.get(f"{BACKEND_URL}/health", timeout=10)
        data = resp.json()
        status = data.get("status", "unknown")
        gpu = data.get("gpu_available", False)
        model = data.get("model_loaded", False)
        db_ok = data.get("database_connected", False)

        if status == "healthy":
            log_pass("Backend /health", f"status={status}")
        else:
            log_warn("Backend /health", f"status={status}")

        if gpu:
            log_pass("GPU available", data.get("gpu_name", ""))
        else:
            log_warn("GPU not available", "FER will be slower on CPU")

        if model:
            log_pass("FER model loaded")
        else:
            log_warn("FER model not loaded", "Emotion detection unavailable")

        if db_ok:
            log_pass("Database connected")
        else:
            log_fail("Database not connected")

        return data
    except requests.exceptions.ConnectionError:
        log_fail("Backend /health", f"Cannot connect to {BACKEND_URL} — is the server running?")
        return None
    except Exception as e:
        log_fail("Backend /health", str(e))
        return None


# ═══════════════════════════════════════════════════════════════════
#  CHECK 2: Database Ping
# ═══════════════════════════════════════════════════════════════════

def check_database():
    log_section("2. Database Connectivity")
    try:
        import requests
        resp = requests.get(f"{BACKEND_URL}/health", timeout=10)
        data = resp.json()
        if data.get("database_connected"):
            log_pass("MongoDB / SQLite reachable via /health")
        else:
            log_fail("Database unreachable", "Check MONGODB_URL or USE_MONGODB setting")
    except ImportError:
        import urllib.request
        try:
            with urllib.request.urlopen(f"{BACKEND_URL}/health", timeout=10) as resp:
                data = json.loads(resp.read().decode())
                if data.get("database_connected"):
                    log_pass("Database reachable via /health")
                else:
                    log_fail("Database unreachable")
        except Exception as e:
            log_fail("Database check", str(e))
    except Exception as e:
        log_fail("Database check", str(e))


# ═══════════════════════════════════════════════════════════════════
#  CHECK 3: ffmpeg Availability
# ═══════════════════════════════════════════════════════════════════

def check_ffmpeg():
    log_section("3. ffmpeg Check")
    ffmpeg_path = shutil.which("ffmpeg")
    if ffmpeg_path:
        try:
            result = subprocess.run(
                ["ffmpeg", "-version"],
                capture_output=True, text=True, timeout=10
            )
            version_line = result.stdout.split("\n")[0] if result.stdout else "unknown"
            log_pass("ffmpeg found", version_line)
        except Exception as e:
            log_warn("ffmpeg found but version check failed", str(e))
    else:
        log_warn("ffmpeg not found in PATH", "Audio processing (Whisper) may not work")


# ═══════════════════════════════════════════════════════════════════
#  CHECK 4: JWT Login Simulation
# ═══════════════════════════════════════════════════════════════════

def check_jwt_login():
    log_section("4. JWT Login Simulation")
    try:
        import requests
    except ImportError:
        log_warn("JWT login check skipped", "requests library not installed")
        return None

    # First try signup, then login
    test_email = f"verify_test_{int(time.time())}@test.com"
    test_password = "TestPass123!"
    test_username = f"verifier_{int(time.time())}"

    try:
        # Attempt signup
        signup_resp = requests.post(
            f"{BACKEND_URL}/auth/signup",
            json={
                "email": test_email,
                "username": test_username,
                "password": test_password,
                "security_question": "What is your favourite colour?",
                "security_answer": "blue",
            },
            timeout=15,
        )

        if signup_resp.status_code in (200, 201):
            log_pass("Signup endpoint", f"status={signup_resp.status_code}")
        else:
            log_warn("Signup endpoint", f"status={signup_resp.status_code} — {signup_resp.text[:100]}")

        # Attempt login
        login_resp = requests.post(
            f"{BACKEND_URL}/auth/login",
            json={"email": test_email, "password": test_password},
            timeout=15,
        )

        if login_resp.status_code == 200:
            data = login_resp.json()
            token = data.get("token", "")
            if token:
                log_pass("Login + JWT token received", f"token length={len(token)}")
                return {"token": token, "user": data.get("user", {})}
            else:
                log_warn("Login succeeded but no token in response")
        else:
            log_warn("Login endpoint", f"status={login_resp.status_code}")

    except requests.exceptions.ConnectionError:
        log_fail("Auth endpoints", f"Cannot connect to {BACKEND_URL}")
    except Exception as e:
        log_fail("Auth endpoints", str(e))

    return None


# ═══════════════════════════════════════════════════════════════════
#  CHECK 5: Interview Session Lifecycle
# ═══════════════════════════════════════════════════════════════════

def check_session_lifecycle(auth_data: dict = None):
    log_section("5. Interview Session Lifecycle")
    try:
        import requests
    except ImportError:
        log_warn("Session lifecycle check skipped", "requests library not installed")
        return

    headers = {}
    if auth_data and auth_data.get("token"):
        headers["Authorization"] = f"Bearer {auth_data['token']}"

    user_id = "test_verify_user"
    if auth_data and auth_data.get("user"):
        user_id = auth_data["user"].get("id", user_id)

    try:
        # Start session
        start_resp = requests.post(
            f"{BACKEND_URL}/interview/start_session",
            json={
                "user_id": user_id,
                "job_role": "Software Engineer",
                "subject": "Python",
                "difficulty": "medium",
            },
            headers=headers,
            timeout=15,
        )

        if start_resp.status_code in (200, 201):
            session_data = start_resp.json()
            session_id = session_data.get("id", "")
            log_pass("Start session", f"session_id={session_id[:12]}...")

            # Get next question
            q_resp = requests.post(
                f"{BACKEND_URL}/interview/next_question",
                json={"session_id": session_id},
                headers=headers,
                timeout=30,
            )

            if q_resp.status_code == 200:
                q_data = q_resp.json()
                log_pass("Next question", f"Q{q_data.get('question_number', '?')}: {q_data.get('question_text', '')[:50]}...")
            else:
                log_warn("Next question", f"status={q_resp.status_code}")

            # End session
            end_resp = requests.post(
                f"{BACKEND_URL}/interview/session/{session_id}/end",
                headers=headers,
                timeout=30,
            )

            if end_resp.status_code == 200:
                log_pass("End session", "Session completed successfully")
            else:
                log_warn("End session", f"status={end_resp.status_code}")
        else:
            log_fail("Start session", f"status={start_resp.status_code} — {start_resp.text[:100]}")

    except requests.exceptions.ConnectionError:
        log_fail("Session lifecycle", f"Cannot connect to {BACKEND_URL}")
    except Exception as e:
        log_fail("Session lifecycle", str(e))


# ═══════════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════════

def main():
    print(f"\n{BOLD}{'='*60}{RESET}")
    print(f"{BOLD}  Smart AI Interview Assistant — Final Verification{RESET}")
    print(f"{BOLD}{'='*60}{RESET}")
    print(f"  Target: {BACKEND_URL}")
    print(f"  Time:   {time.strftime('%Y-%m-%d %H:%M:%S')}")

    check_backend_health()
    check_database()
    check_ffmpeg()
    auth_data = check_jwt_login()
    check_session_lifecycle(auth_data)

    # ── Summary ──────────────────────────────────────────────────
    print(f"\n{BOLD}{'='*60}{RESET}")
    passes = sum(1 for r in results if r[0] == "PASS")
    fails = sum(1 for r in results if r[0] == "FAIL")
    warns = sum(1 for r in results if r[0] == "WARN")
    total = len(results)

    print(f"  {GREEN}PASS: {passes}{RESET}  |  {YELLOW}WARN: {warns}{RESET}  |  {RED}FAIL: {fails}{RESET}  |  Total: {total}")

    if fails == 0:
        print(f"\n  {GREEN}{BOLD}{'*'*50}{RESET}")
        print(f"  {GREEN}{BOLD}  SYSTEM READY FOR CLIENT{RESET}")
        print(f"  {GREEN}{BOLD}{'*'*50}{RESET}\n")
        sys.exit(0)
    else:
        print(f"\n  {RED}{BOLD}  SYSTEM NOT READY — {fails} check(s) failed{RESET}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
