"""
Authentication Router
=====================
Signup, Login, and Password Reset — backed by SQLite.
Hashing: passlib (pbkdf2_sha256)     Tokens: python-jose (JWT)
"""

import logging
import time
from collections import defaultdict
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import jwt, JWTError
from passlib.context import CryptContext

from app.config import settings
from app import database as db
from app.models import UserSignup, UserLogin, PasswordReset, Token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


# ---------------------------------------------------------------------------
# Simple in-memory rate limiter (per IP)
# ---------------------------------------------------------------------------
_rate_buckets: dict[str, list[float]] = defaultdict(list)


def _check_rate_limit(ip: str, limit: int, window: int = 60):
    """
    Raise 429 if *ip* has exceeded *limit* requests in the last *window* seconds.
    """
    now = time.time()
    bucket = _rate_buckets[ip]
    # Prune stale entries
    _rate_buckets[ip] = bucket = [t for t in bucket if now - t < window]
    if len(bucket) >= limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many requests. Try again in {window} seconds.",
        )
    bucket.append(now)

# ---------------------------------------------------------------------------
# Security utilities
# ---------------------------------------------------------------------------
# Switched to pbkdf2_sha256 to avoid bcrypt's 72-byte limit and Windows build issues
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

SECRET_KEY = settings.jwt_secret_key
ALGORITHM = settings.jwt_algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = settings.jwt_expire_minutes


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


# ---------------------------------------------------------------------------
# Dependency: extract current user from JWT
# ---------------------------------------------------------------------------
_bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
) -> dict:
    """
    Decode the JWT from the Authorization header and return the payload.
    Returns {"sub": "<user_id>", "role": "<role>"}.
    Raises 401 if missing/invalid.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        role: str = payload.get("role", "student")
        if user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        return {"sub": user_id, "role": role}
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )


# ============================================================================
# POST /auth/signup
# ============================================================================

def _mask(value: str, visible: int = 3) -> str:
    """Mask PII for safe logging: 'user@mail.com' -> 'use***@m***.com'."""
    if not value:
        return "***"
    if "@" in value:
        local, domain = value.split("@", 1)
        return f"{local[:visible]}***@{domain[0]}***"
    return f"{value[:visible]}***"


@router.post("/signup")
async def signup(user: UserSignup, request: Request):
    """Register a new user."""
    _check_rate_limit(request.client.host, settings.rate_limit_signup_per_minute)
    logger.info(f"Signup request: email={_mask(user.email)}, username={_mask(user.username)}")

    try:
        # --- duplicate check ---
        if await db.users_collection.find_one({"email": user.email}):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )

        if await db.users_collection.find_one({"username": user.username}):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken",
            )

        hp = hash_password(user.password)
        hsa = hash_password(user.security_answer.lower().strip())

        # --- build document ---
        user_doc = {
            "username": user.username,
            "email": user.email,
            "hashed_password": hp,
            "security_question": user.security_question,
            "security_answer_hash": hsa,
            "role": "student",
            "created_at": datetime.utcnow(),
        }

        await db.users_collection.insert_one(user_doc)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Signup failed: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

    return {"msg": "User created"}


# ============================================================================
# POST /auth/login
# ============================================================================

# ---------------------------------------------------------------------------
# Account lockout — per-email failed attempt tracker
# ---------------------------------------------------------------------------
_MAX_FAILED_ATTEMPTS = 7
_LOCKOUT_SECONDS = 300  # 5 minutes
_failed_logins: dict[str, list[float]] = defaultdict(list)


def _check_lockout(email: str):
    """Raise 429 if the account has exceeded max failed login attempts."""
    now = time.time()
    bucket = _failed_logins.get(email, [])
    # Keep only attempts within the lockout window
    bucket = [t for t in bucket if now - t < _LOCKOUT_SECONDS]
    _failed_logins[email] = bucket
    if len(bucket) >= _MAX_FAILED_ATTEMPTS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Account temporarily locked after {_MAX_FAILED_ATTEMPTS} failed attempts. "
                   f"Try again in {_LOCKOUT_SECONDS // 60} minutes.",
        )


def _record_failed_login(email: str):
    _failed_logins[email].append(time.time())


def _clear_failed_logins(email: str):
    _failed_logins.pop(email, None)


@router.post("/login", response_model=Token)
async def login(creds: UserLogin, request: Request):
    """Authenticate a user by email and return a JWT."""
    _check_rate_limit(request.client.host, settings.rate_limit_login_per_minute)
    _check_lockout(creds.email)

    user = await db.users_collection.find_one({"email": creds.email})

    if not user or not verify_password(creds.password, user["hashed_password"]):
        _record_failed_login(creds.email)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email/username or password",
        )

    # Successful login — clear any lockout state
    _clear_failed_logins(creds.email)

    token_data = {
        "sub": str(user["_id"]),
        "role": user.get("role", "student"),
        "username": user.get("username", ""),
        "email": user.get("email", ""),
    }
    access_token = create_access_token(token_data)

    return Token(
        access_token=access_token,
        token_type="bearer",
        role=user.get("role", "student"),
    )


# ============================================================================
# GET /auth/security-question
# ============================================================================

@router.get("/security-question")
async def get_security_question(email: str):
    """
    Return the security question for a given email address.
    Used by the Forgot Password flow (step 1).
    """
    user = await db.users_collection.find_one({"email": email})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No account found with that email address",
        )
    return {"security_question": user.get("security_question", "")}


# ============================================================================
# POST /auth/reset-password
# ============================================================================

@router.post("/reset-password")
async def reset_password(data: PasswordReset, request: Request):
    """Reset a user's password via security-question verification."""
    _check_rate_limit(request.client.host, settings.rate_limit_login_per_minute)

    user = await db.users_collection.find_one({"email": data.email})

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Compare security answer (case-insensitive, trimmed)
    if not verify_password(data.security_answer.lower().strip(), user["security_answer_hash"]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect security answer",
        )

    # Update the password
    await db.users_collection.update_one(
        {"_id": user["_id"]},
        {"$set": {"hashed_password": hash_password(data.new_password)}},
    )

    return {"msg": "Password updated successfully"}


async def ensure_admin_user():
    """
    Create a default admin user ONLY if no admin users exist at all.
    Credentials are read from environment/config — never hardcoded.
    """
    # Check if ANY admin already exists
    existing_admin = await db.users_collection.find_one({"role": "admin"})
    if existing_admin:
        logger.info("Admin user already exists — skipping creation.")
        return

    admin_email = settings.admin_email
    admin_pass = settings.admin_password

    # Warn if using the insecure default password
    if admin_pass == "admin":
        logger.warning(
            "!! Creating admin with default password 'admin'. "
            "Set ADMIN_PASSWORD in .env for production!"
        )

    logger.info(f"No admin users found — creating default: {admin_email}")
    hp = hash_password(admin_pass)
    user_doc = {
        "username": "admin",
        "email": admin_email,
        "hashed_password": hp,
        "security_question": "default",
        "security_answer_hash": hash_password("default"),
        "role": "admin",
        "created_at": datetime.utcnow(),
    }
    await db.users_collection.insert_one(user_doc)
    logger.info(f"Admin user created: {admin_email}")
