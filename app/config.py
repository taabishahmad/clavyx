"""Central configuration.

Everything sensitive comes from environment variables (loaded from a local .env
file in development) so that no secret ever lives in the source code. If you are
new to this: copy .env.example to .env and you are good to go.
"""
from __future__ import annotations
import os
import secrets
from dotenv import load_dotenv

load_dotenv()  # reads a local .env file if present; harmless if it is missing


def _flag(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


class Settings:
    """A tiny settings object. Kept deliberately simple and readable."""

    APP_NAME = "CLAVYX"
    TAGLINE = "Find the key your conclusion rests on."

    # If no secret is provided we generate a throwaway one so the app still runs,
    # but we warn loudly, because that means sessions reset on every restart.
    SECRET_KEY = os.getenv("CLAVYX_SECRET_KEY") or secrets.token_hex(32)
    SECRET_IS_EPHEMERAL = os.getenv("CLAVYX_SECRET_KEY") is None

    # Session / token lifetimes.
    SESSION_MINUTES = 60 * 8            # normal login lasts 8 hours
    SESSION_REMEMBER_DAYS = 30         # "remember me" lasts 30 days
    RESET_TOKEN_MINUTES = 30           # password reset link validity

    # Cookie security. Keep false on http://localhost, set true behind HTTPS.
    COOKIE_SECURE = _flag("CLAVYX_COOKIE_SECURE", False)

    # Brute force protection.
    MAX_FAILED_LOGINS = 5
    LOCKOUT_MINUTES = 15

    # Simple in-memory rate limiting (per process). Production would use Redis.
    RATE_LIMIT_WINDOW_SECONDS = 60
    RATE_LIMIT_MAX_REQUESTS = 20       # generic endpoints
    ANALYZE_LIMIT_PER_MINUTE = 8       # the expensive analyze endpoint

    # Database. SQLite needs zero setup and is perfect for a final year project.
    DB_URL = os.getenv("CLAVYX_DB_URL", "sqlite:///./clavyx.db")

    # AI provider selection.
    LLM_PROVIDER = os.getenv("CLAVYX_LLM_PROVIDER", "mock").strip().lower()
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
    OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").strip()
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip()
    GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
    GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant").strip()
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "").strip()
    ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-3-5-haiku-latest").strip()

    CONTACT_EMAIL = "tabishahmad2021@gmail.com"
    CONTACT_GITHUB = "https://github.com/taabishahmad"
    CONTACT_LINKEDIN = "https://linkedin.com/in/taabishahmad"


settings = Settings()
