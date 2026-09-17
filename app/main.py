"""Application entry point. Run with:  uvicorn app.main:app --reload"""
from __future__ import annotations
import logging
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse

from .config import settings
from .database import init_db
from .deps import render, AuthRedirect, CSRF_COOKIE
from .security import new_csrf_token
from .routers import pages, auth, app_views, api, admin

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("clavyx")

app = FastAPI(title=settings.APP_NAME, docs_url=None, redoc_url=None)
app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(pages.router)
app.include_router(auth.router)
app.include_router(app_views.router)
app.include_router(api.router)
app.include_router(admin.router)

# Create database tables as soon as the app is imported. Safe to run repeatedly;
# it is a no-op once the tables exist. Doing it here (not only on startup) means
# the app works no matter how it is launched.
init_db()


@app.on_event("startup")
def _startup() -> None:
    init_db()
    if settings.SECRET_IS_EPHEMERAL:
        log.warning("CLAVYX_SECRET_KEY is not set. Using a temporary key: logins "
                    "reset on restart. Set one in .env for real use.")
    log.info("CLAVYX ready. AI provider in use: %s", __import__(
        "app.services.llm_provider", fromlist=["active_provider"]).active_provider())


@app.middleware("http")
async def security_and_csrf(request: Request, call_next):
    """Add strong security headers to every response and make sure a CSRF token
    cookie exists for form pages."""
    ensure_csrf = request.cookies.get(CSRF_COOKIE) is None
    token = request.cookies.get(CSRF_COOKIE) or new_csrf_token()

    response = await call_next(request)

    if ensure_csrf:
        response.set_cookie(
            CSRF_COOKIE, token, httponly=False, samesite="lax",
            secure=settings.COOKIE_SECURE, max_age=60 * 60 * 24,
        )
    # Security headers. The content security policy is fairly strict: scripts and
    # styles load only from our own origin (plus Google Fonts for typography).
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data:; "
        "connect-src 'self'; frame-ancestors 'none'; base-uri 'self'"
    )
    return response


@app.exception_handler(AuthRedirect)
async def _auth_redirect(request: Request, exc: AuthRedirect):
    return RedirectResponse(url="/login?next=" + request.url.path, status_code=303)


@app.exception_handler(404)
async def _not_found(request: Request, exc):
    return render(request, "errors/404.html", status_code=404)


@app.exception_handler(500)
async def _server_error(request: Request, exc):
    log.exception("Unhandled error")
    return render(request, "errors/500.html", status_code=500)
