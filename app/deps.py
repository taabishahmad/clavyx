"""Shared request helpers: the template renderer, the current user lookup, and
the small redirect trick that sends signed-out visitors to the login page."""
from __future__ import annotations
from datetime import datetime
from fastapi import Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from .database import get_db
from .models import User
from .security import read_session_token
from .config import settings

templates = Jinja2Templates(directory="app/templates")

SESSION_COOKIE = "clavyx_session"
CSRF_COOKIE = "clavyx_csrf"


class AuthRedirect(Exception):
    """Raised inside a page route when a signed-out user hits a protected page.
    A handler in main.py turns it into a redirect to the login screen."""


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User | None:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        return None
    uid = read_session_token(token)
    if uid is None:
        return None
    return db.get(User, uid)


def require_user(request: Request, db: Session = Depends(get_db)) -> User:
    user = get_current_user(request, db)
    if user is None:
        raise AuthRedirect()
    return user


def render(request: Request, template: str, user: User | None = None, **ctx) -> HTMLResponse:
    """Render a template with the common context every page needs, so individual
    routes stay clean."""
    base = {
        "request": request,
        "user": user,
        "csrf_token": request.cookies.get(CSRF_COOKIE, ""),
        "settings": settings,
        "year": datetime.now().year,
        "active": ctx.pop("active", ""),
    }
    status_code = ctx.pop("status_code", 200)
    base.update(ctx)
    # Modern Starlette signature: (request, name, context, ...).
    return templates.TemplateResponse(request, template, base, status_code=status_code)
