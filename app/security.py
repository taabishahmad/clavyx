"""All the security primitives in one place: password hashing, session tokens,
CSRF protection, rate limiting and account lockout.

Design notes for reviewers:
- Passwords use PBKDF2-SHA256 (pure Python, no native build needed). bcrypt or
  Argon2 are drop-in replacements: add the dependency and change the scheme list.
- The session is a signed JWT stored in an httpOnly cookie, so JavaScript on the
  page can never read it, which blocks token theft via cross site scripting.
- CSRF uses the double submit pattern: a signed token lives in a readable cookie
  and must be echoed back in every state changing request.
"""
from __future__ import annotations
import re
import time
import secrets
from datetime import datetime, timedelta, timezone
from collections import defaultdict, deque

import jwt
from passlib.context import CryptContext
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

from .config import settings

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
_serializer = URLSafeTimedSerializer(settings.SECRET_KEY, salt="clavyx-tokens")

ALGO = "HS256"

# A password must be 8 to 128 characters and contain at least one letter and one
# digit. Kept here so both the schema and the reset flow share one definition.
PASSWORD_RULE = re.compile(r"^(?=.*[A-Za-z])(?=.*\d).{8,128}$")


# ---------- passwords ----------
def hash_password(raw: str) -> str:
    return pwd_context.hash(raw)


def verify_password(raw: str, hashed: str) -> bool:
    try:
        return pwd_context.verify(raw, hashed)
    except ValueError:
        return False


# ---------- session tokens (JWT) ----------
def create_session_token(user_id: int, remember: bool = False) -> str:
    now = datetime.now(timezone.utc)
    delta = (timedelta(days=settings.SESSION_REMEMBER_DAYS)
             if remember else timedelta(minutes=settings.SESSION_MINUTES))
    payload = {"sub": str(user_id), "iat": now, "exp": now + delta, "typ": "session"}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGO)


def read_session_token(token: str) -> int | None:
    try:
        data = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGO])
        if data.get("typ") != "session":
            return None
        return int(data["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        return None


# ---------- signed one-time links (reset / verify) ----------
def make_link_token(user_id: int, purpose: str) -> str:
    return _serializer.dumps({"uid": user_id, "p": purpose})


def read_link_token(token: str, purpose: str, max_age_seconds: int) -> int | None:
    try:
        data = _serializer.loads(token, max_age=max_age_seconds)
    except (BadSignature, SignatureExpired):
        return None
    if data.get("p") != purpose:
        return None
    return int(data.get("uid"))


# ---------- CSRF (double submit) ----------
def new_csrf_token() -> str:
    return secrets.token_urlsafe(24)


def csrf_ok(cookie_token: str | None, sent_token: str | None) -> bool:
    return bool(cookie_token) and bool(sent_token) and secrets.compare_digest(cookie_token, sent_token)


# ---------- account lockout ----------
def is_locked(user) -> bool:
    if not user.locked_until:
        return False
    return datetime.utcnow() < user.locked_until


def register_failed_login(db, user) -> None:
    user.failed_attempts = (user.failed_attempts or 0) + 1
    if user.failed_attempts >= settings.MAX_FAILED_LOGINS:
        user.locked_until = datetime.utcnow() + timedelta(minutes=settings.LOCKOUT_MINUTES)
        user.failed_attempts = 0
    db.commit()


def register_successful_login(db, user) -> None:
    user.failed_attempts = 0
    user.locked_until = None
    db.commit()


# ---------- rate limiting (in memory, per process) ----------
# For a single process this is fine. Production would move this to Redis so it
# works across many servers. Kept simple and honest here.
_hits: dict[str, deque] = defaultdict(deque)


def rate_limit(key: str, max_requests: int, window: int = 60) -> bool:
    """Return True if the caller is still within the allowed rate, False if they
    have exceeded it."""
    now = time.time()
    bucket = _hits[key]
    while bucket and now - bucket[0] > window:
        bucket.popleft()
    if len(bucket) >= max_requests:
        return False
    bucket.append(now)
    return True
