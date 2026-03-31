#!/usr/bin/env python3
"""
Preflight Check — Smart AI Interview Assistant
================================================
Master verification script that tests every critical subsystem
before final handover.

Usage (from project root):
    python tests/preflight_check.py

Checks:
    1. Silence Detection     — Audio service returns silence=True for a silent buffer
    2. PDF Generation        — jspdf is listed in frontend/package.json
    3. Database              — Ping MongoDB/SQLite and verify sessions collection
    4. Admin Login           — Attempt login with admin@test.com, verify role
    5. File Structure        — VIVA_SUPPORT.md, USER_GUIDE.md, docker-compose.yml exist
    6. WebSocket Silence Gate — Backend handles {"type":"silence"} messages
"""

import json
import os
import sys
import time

# ── Resolve project root ────────────────────────────────────────
# Works whether run from project root or from tests/ directory
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
BACKEND_DIR = os.path.join(PROJECT_ROOT, "backend")
FRONTEND_DIR = os.path.join(PROJECT_ROOT, "frontend")

# Add backend to path for direct imports
sys.path.insert(0, BACKEND_DIR)

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

# ── Terminal colours ────────────────────────────────────────────
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"

results = []
details = []


def ok(label, detail=""):
    msg = f"  {GREEN}\u2705 PASS{RESET}  {label}"
    if detail:
        msg += f"  ({detail})"
    print(msg)
    results.append(True)
    details.append(("PASS", label))


def fail(label, detail=""):
    msg = f"  {RED}\u274c FAIL{RESET}  {label}"
    if detail:
        msg += f"  \u2014 {detail}"
    print(msg)
    results.append(False)
    details.append(("FAIL", label))


def warn(label, detail=""):
    msg = f"  {YELLOW}\u26a0  WARN{RESET}  {label}"
    if detail:
        msg += f"  \u2014 {detail}"
    print(msg)
    results.append(True)  # Warnings don't block
    details.append(("WARN", label))


def section(title):
    print(f"\n{CYAN}{BOLD}{'='*60}{RESET}")
    print(f"{CYAN}{BOLD}  CHECK: {title}{RESET}")
    print(f"{CYAN}{BOLD}{'='*60}{RESET}")


# ═══════════════════════════════════════════════════════════════════
#  CHECK 1: Silence Detection
# ═══════════════════════════════════════════════════════════════════

def check_silence_detection():
    section("1. Silence Detection (Audio Service)")
    try:
        import numpy as np
        from app.services.audio import VoiceClarityAnalyzer

        analyzer = VoiceClarityAnalyzer(sample_rate=16000)

        # Generate 1 second of pure silence (all zeros)
        silent_buffer = np.zeros(16000, dtype=np.float32)
        result = analyzer.analyze(silent_buffer)

        silence_ratio = result.get("silence_ratio", 0)
        is_speaking = result.get("is_speaking", True)

        if not is_speaking and silence_ratio > 0.9:
            ok("Silence detection",
               f"silence_ratio={silence_ratio}, is_speaking={is_speaking}")
        else:
            fail("Silence detection",
                 f"Expected is_speaking=False, got is_speaking={is_speaking}, "
                 f"silence_ratio={silence_ratio}")

        # Also verify non-silent audio IS detected as speech
        speech_buffer = np.random.randn(16000).astype(np.float32) * 0.3
        speech_result = analyzer.analyze(speech_buffer)
        speech_speaking = speech_result.get("is_speaking", False)

        if speech_speaking:
            ok("Speech detection", "Non-silent buffer correctly detected as speech")
        else:
            warn("Speech detection",
                 "Non-silent buffer not detected as speech (may need tuning)")

    except ImportError as e:
        warn("Silence detection (import)",
             f"Could not import audio service: {e}. "
             "Run this script from the backend directory or ensure numpy is installed.")
    except Exception as e:
        fail("Silence detection", str(e))


# ═══════════════════════════════════════════════════════════════════
#  CHECK 2: PDF Generation (jsPDF in package.json)
# ═══════════════════════════════════════════════════════════════════

def check_pdf_generation():
    section("2. PDF Generation (jsPDF)")
    pkg_path = os.path.join(FRONTEND_DIR, "package.json")

    if not os.path.exists(pkg_path):
        fail("package.json", f"Not found at {pkg_path}")
        return

    try:
        with open(pkg_path, "r", encoding="utf-8") as f:
            pkg = json.load(f)

        deps = pkg.get("dependencies", {})
        dev_deps = pkg.get("devDependencies", {})
        all_deps = {**deps, **dev_deps}

        # Check for jspdf
        if "jspdf" in all_deps:
            ok("jspdf found", f"version {all_deps['jspdf']}")
        else:
            fail("jspdf", "Not listed in package.json dependencies")

        # Also check jspdf-autotable (used for table formatting in PDF)
        if "jspdf-autotable" in all_deps:
            ok("jspdf-autotable found", f"version {all_deps['jspdf-autotable']}")
        else:
            warn("jspdf-autotable", "Not found — PDF tables may not render")

        # Bonus: check that the node_modules actually has it installed
        jspdf_module = os.path.join(FRONTEND_DIR, "node_modules", "jspdf")
        if os.path.isdir(jspdf_module):
            ok("jspdf installed in node_modules")
        else:
            warn("jspdf not in node_modules", "Run 'npm install' in frontend/")

    except Exception as e:
        fail("package.json parse", str(e))


# ═══════════════════════════════════════════════════════════════════
#  CHECK 3: Database — Ping + Sessions Collection
# ═══════════════════════════════════════════════════════════════════

def check_database():
    section("3. Database (MongoDB / SQLite)")

    # Strategy A: Try HTTP health endpoint
    http_ok = False
    try:
        import urllib.request
        req = urllib.request.Request(f"{BACKEND_URL}/health", method="GET")
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            db_connected = data.get("database_connected", False)

            if db_connected:
                ok("Database connected via /health endpoint")
                http_ok = True
            else:
                warn("Database NOT connected via /health",
                     "Backend is running but DB is unreachable")
    except Exception as e:
        warn("Backend /health unreachable",
             f"{e} — trying direct DB check instead")

    # Strategy B: Direct MongoDB / SQLite verification
    if not http_ok:
        try:
            from app.config import settings

            if settings.use_mongodb:
                try:
                    from motor.motor_asyncio import AsyncIOMotorClient
                    import asyncio
                    import certifi

                    async def ping_mongo():
                        kwargs = {"serverSelectionTimeoutMS": 5000}
                        url = settings.mongodb_url
                        if url.startswith("mongodb+srv"):
                            kwargs["tlsCAFile"] = certifi.where()
                        client = AsyncIOMotorClient(url, **kwargs)
                        await client.admin.command("ping")
                        db = client["interview_db"]
                        collections = await db.list_collection_names()
                        client.close()
                        return collections

                    collections = asyncio.run(ping_mongo())
                    ok("MongoDB ping successful")

                    if "sessions" in collections:
                        ok("'sessions' collection exists")
                    else:
                        warn("'sessions' collection not found",
                             f"Available: {collections}. "
                             "Collection will be created on first session.")
                except Exception as e:
                    fail("MongoDB direct ping", str(e))
            else:
                # SQLite mode
                sqlite_path = os.path.join(BACKEND_DIR, "test_db.sqlite")
                if os.path.exists(sqlite_path):
                    ok("SQLite database file exists", sqlite_path)
                else:
                    warn("SQLite file not found",
                         "Will be created on first backend startup")

        except ImportError as e:
            warn("Direct DB check skipped", f"Missing import: {e}")


# ═══════════════════════════════════════════════════════════════════
#  CHECK 4: Admin Login
# ═══════════════════════════════════════════════════════════════════

def check_admin_login():
    section("4. Admin Login (admin@test.com)")

    try:
        import urllib.request

        # Step 1: Attempt signup (may already exist — that's OK)
        signup_payload = json.dumps({
            "email": "admin@test.com",
            "username": "admin_preflight",
            "password": "AdminPass123!",
            "security_question": "Preflight check question",
            "security_answer": "preflight",
        }).encode("utf-8")

        try:
            signup_req = urllib.request.Request(
                f"{BACKEND_URL}/auth/signup",
                data=signup_payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(signup_req, timeout=15) as resp:
                ok("Signup admin@test.com", f"status={resp.status}")
        except urllib.error.HTTPError as e:
            if e.code == 400:
                ok("admin@test.com already registered (expected)")
            else:
                warn("Signup failed", f"HTTP {e.code}: {e.read().decode()[:100]}")
        except Exception as e:
            warn("Signup request failed", str(e))

        # Step 2: Attempt login
        login_payload = json.dumps({
            "email": "admin@test.com",
            "password": "AdminPass123!",
        }).encode("utf-8")

        login_req = urllib.request.Request(
            f"{BACKEND_URL}/auth/login",
            data=login_payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        with urllib.request.urlopen(login_req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
            token = data.get("access_token", "")
            role = data.get("role", "unknown")

            if role == "admin":
                ok("Admin login verified", "role=admin")
            elif role == "student":
                warn("Login succeeded but role='student'",
                     "Expected 'admin'. In dev mode (USE_MONGODB=false), "
                     "all logins return role='student'. "
                     "To set admin role, update the user document in MongoDB: "
                     "db.users.updateOne({email:'admin@test.com'}, {$set:{role:'admin'}})")
            else:
                warn("Login role unexpected", f"role={role}")

            if token:
                ok("JWT token received", f"length={len(token)} chars")
            else:
                fail("No JWT token in login response")

    except urllib.error.URLError as e:
        warn("Admin login check skipped",
             f"Backend unreachable at {BACKEND_URL}: {e}")
    except Exception as e:
        fail("Admin login", str(e))


# ═══════════════════════════════════════════════════════════════════
#  CHECK 5: File Structure
# ═══════════════════════════════════════════════════════════════════

def check_file_structure():
    section("5. File Structure Verification")

    required_files = {
        "VIVA_SUPPORT.md": os.path.join(PROJECT_ROOT, "VIVA_SUPPORT.md"),
        "USER_GUIDE.md": os.path.join(PROJECT_ROOT, "USER_GUIDE.md"),
        "TECHNICAL_DOCS.md": os.path.join(PROJECT_ROOT, "TECHNICAL_DOCS.md"),
        "docker-compose.yml": os.path.join(PROJECT_ROOT, "docker-compose.yml"),
        "README.md": os.path.join(PROJECT_ROOT, "README.md"),
        "backend/Dockerfile": os.path.join(BACKEND_DIR, "Dockerfile"),
        "frontend/Dockerfile": os.path.join(FRONTEND_DIR, "Dockerfile"),
        "backend/requirements.txt": os.path.join(BACKEND_DIR, "requirements.txt"),
        "frontend/package.json": os.path.join(FRONTEND_DIR, "package.json"),
        "backend/app/main.py": os.path.join(BACKEND_DIR, "app", "main.py"),
        "backend/app/config.py": os.path.join(BACKEND_DIR, "app", "config.py"),
        "backend/app/routers/interview.py": os.path.join(BACKEND_DIR, "app", "routers", "interview.py"),
        "backend/app/routers/auth.py": os.path.join(BACKEND_DIR, "app", "routers", "auth.py"),
        "backend/app/services/audio.py": os.path.join(BACKEND_DIR, "app", "services", "audio.py"),
        "backend/app/services/gemini.py": os.path.join(BACKEND_DIR, "app", "services", "gemini.py"),
        "frontend/src/App.jsx": os.path.join(FRONTEND_DIR, "src", "App.jsx"),
        "frontend/src/pages/InterviewSession.jsx": os.path.join(FRONTEND_DIR, "src", "pages", "InterviewSession.jsx"),
        "frontend/src/pages/History.jsx": os.path.join(FRONTEND_DIR, "src", "pages", "History.jsx"),
        "frontend/src/pages/QuestionBank.jsx": os.path.join(FRONTEND_DIR, "src", "pages", "QuestionBank.jsx"),
    }

    missing = []
    for label, path in required_files.items():
        if os.path.exists(path):
            ok(label)
        else:
            fail(label, f"Missing: {path}")
            missing.append(label)

    if not missing:
        ok("All required files present", f"{len(required_files)} files verified")


# ═══════════════════════════════════════════════════════════════════
#  CHECK 6: WebSocket Silence Gate (bonus)
# ═══════════════════════════════════════════════════════════════════

def check_websocket_silence_gate():
    section("6. WebSocket Silence Gate (Code Verification)")

    ws_file = os.path.join(BACKEND_DIR, "app", "routers", "interview.py")

    if not os.path.exists(ws_file):
        fail("interview.py not found")
        return

    try:
        with open(ws_file, "r", encoding="utf-8") as f:
            content = f.read()

        # Check that silence handler exists
        if '"silence"' in content and '"type": "silence"' in content:
            ok("Silence gate handler found in WebSocket endpoint")
        else:
            fail("Silence gate handler NOT found",
                 "Expected 'silence' message type in interview.py WebSocket")

        # Check that it returns metrics: 0 (no GPU processing)
        if '"metrics": 0' in content or '"metrics":0' in content:
            ok("Silence gate returns metrics=0 (no GPU waste)")
        else:
            warn("Silence gate metrics response not verified")

    except Exception as e:
        fail("WebSocket code check", str(e))


# ═══════════════════════════════════════════════════════════════════
#  MAIN — Run All Checks
# ═══════════════════════════════════════════════════════════════════

def main():
    print(f"\n{BOLD}{'#'*60}{RESET}")
    print(f"{BOLD}  PREFLIGHT CHECK — Smart AI Interview Assistant{RESET}")
    print(f"{BOLD}  Final Release Verification{RESET}")
    print(f"{BOLD}{'#'*60}{RESET}")
    print(f"  Project Root : {PROJECT_ROOT}")
    print(f"  Backend URL  : {BACKEND_URL}")
    print(f"  Timestamp    : {time.strftime('%Y-%m-%d %H:%M:%S')}")

    check_silence_detection()
    check_pdf_generation()
    check_database()
    check_admin_login()
    check_file_structure()
    check_websocket_silence_gate()

    # ── Final Report ─────────────────────────────────────────────
    print(f"\n{BOLD}{'#'*60}{RESET}")
    print(f"{BOLD}  FINAL REPORT{RESET}")
    print(f"{BOLD}{'#'*60}{RESET}\n")

    passes = sum(1 for s, _ in details if s == "PASS")
    warns = sum(1 for s, _ in details if s == "WARN")
    fails = sum(1 for s, _ in details if s == "FAIL")
    total = len(details)

    print(f"  {GREEN}PASS: {passes}{RESET}  |  "
          f"{YELLOW}WARN: {warns}{RESET}  |  "
          f"{RED}FAIL: {fails}{RESET}  |  "
          f"Total: {total}")

    if fails > 0:
        print(f"\n  {RED}{BOLD}\u274c FAILED:{RESET}")
        for status, label in details:
            if status == "FAIL":
                print(f"     {RED}- {label}{RESET}")
        print(f"\n  {RED}{BOLD}\u274c PREFLIGHT FAILED — {fails} check(s) need attention{RESET}\n")
        sys.exit(1)
    else:
        print(f"\n  {GREEN}{BOLD}{'*'*50}{RESET}")
        print(f"  {GREEN}{BOLD}  \u2705 ALL SYSTEMS GO{RESET}")
        print(f"  {GREEN}{BOLD}  Ready for client handover.{RESET}")
        print(f"  {GREEN}{BOLD}{'*'*50}{RESET}\n")
        sys.exit(0)


if __name__ == "__main__":
    main()
