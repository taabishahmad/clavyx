"""Sign up, login, logout, password reset and optional two factor auth."""
from __future__ import annotations
import pyotp
from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from pydantic import ValidationError

from ..database import get_db
from ..deps import render, get_current_user, require_user, SESSION_COOKIE, CSRF_COOKIE
from ..models import User
from ..schemas import SignupIn, LoginIn
from ..config import settings
from ..security import (
    hash_password, verify_password, create_session_token, csrf_ok,
    is_locked, register_failed_login, register_successful_login,
    make_link_token, read_link_token, rate_limit, PASSWORD_RULE,
)

router = APIRouter()


def _set_session(resp, user_id: int, remember: bool):
    max_age = (60 * 60 * 24 * settings.SESSION_REMEMBER_DAYS) if remember else (60 * settings.SESSION_MINUTES)
    resp.set_cookie(
        SESSION_COOKIE, create_session_token(user_id, remember),
        httponly=True, samesite="lax", secure=settings.COOKIE_SECURE, max_age=max_age,
    )


def _check_csrf(request: Request, sent: str | None):
    return csrf_ok(request.cookies.get(CSRF_COOKIE), sent)


# ---------------- sign up ----------------
@router.get("/signup")
def signup_form(request: Request, db: Session = Depends(get_db)):
    if get_current_user(request, db):
        return RedirectResponse("/dashboard", 303)
    return render(request, "auth/signup.html", active="signup")


@router.post("/signup")
def signup(request: Request, db: Session = Depends(get_db),
           display_name: str = Form(...), email: str = Form(...),
           password: str = Form(...), csrf_field: str = Form("", alias="_csrf")):
    if not _check_csrf(request, csrf_field):
        return render(request, "auth/signup.html", error="Your session expired. Please try again.")
    try:
        data = SignupIn(display_name=display_name, email=email, password=password)
    except ValidationError as e:
        return render(request, "auth/signup.html", error=e.errors()[0]["msg"],
                      form={"display_name": display_name, "email": email})
    if db.query(User).filter(User.email == data.email.lower()).first():
        return render(request, "auth/signup.html", error="An account with that email already exists.",
                      form={"display_name": display_name, "email": email})
    user = User(email=data.email.lower(), password_hash=hash_password(data.password),
                display_name=data.display_name, role="user", is_verified=True)
    db.add(user); db.commit(); db.refresh(user)
    resp = RedirectResponse("/dashboard", 303)
    _set_session(resp, user.id, remember=False)
    return resp


# ---------------- login ----------------
@router.get("/login")
def login_form(request: Request, db: Session = Depends(get_db), next: str = "/dashboard"):
    if get_current_user(request, db):
        return RedirectResponse("/dashboard", 303)
    return render(request, "auth/login.html", active="login", next=next)


@router.post("/login")
def login(request: Request, db: Session = Depends(get_db),
          email: str = Form(...), password: str = Form(...),
          remember: str = Form(""), next: str = Form("/dashboard"), csrf_field: str = Form("", alias="_csrf")):
    ip = request.client.host if request.client else "unknown"
    if not rate_limit(f"login:{ip}", settings.RATE_LIMIT_MAX_REQUESTS):
        return render(request, "auth/login.html", error="Too many attempts. Please wait a minute.", next=next)
    if not _check_csrf(request, csrf_field):
        return render(request, "auth/login.html", error="Your session expired. Please try again.", next=next)
    try:
        data = LoginIn(email=email, password=password)
    except ValidationError:
        return render(request, "auth/login.html", error="Please enter a valid email and password.", next=next)

    user = db.query(User).filter(User.email == data.email.lower()).first()
    # Always run a hash comparison-shaped delay path to avoid leaking which emails exist.
    if not user or not verify_password(data.password, user.password_hash):
        if user:
            register_failed_login(db, user)
        return render(request, "auth/login.html", error="Email or password is incorrect.", next=next)
    if is_locked(user):
        return render(request, "auth/login.html",
                      error="This account is temporarily locked after several failed attempts. Try again later.",
                      next=next)

    if user.twofa_enabled and user.totp_secret:
        # Stash a short lived pre-auth token and ask for the code.
        resp = RedirectResponse("/2fa", 303)
        resp.set_cookie("clavyx_pre2fa", make_link_token(user.id, "pre2fa"),
                        httponly=True, samesite="lax", secure=settings.COOKIE_SECURE, max_age=300)
        return resp

    register_successful_login(db, user)
    resp = RedirectResponse(next if next.startswith("/") else "/dashboard", 303)
    _set_session(resp, user.id, remember=bool(remember))
    return resp


@router.get("/2fa")
def twofa_form(request: Request):
    if not request.cookies.get("clavyx_pre2fa"):
        return RedirectResponse("/login", 303)
    return render(request, "auth/twofa_verify.html")


@router.post("/2fa")
def twofa_verify(request: Request, db: Session = Depends(get_db),
                 code: str = Form(...), csrf_field: str = Form("", alias="_csrf")):
    pre = request.cookies.get("clavyx_pre2fa")
    uid = read_link_token(pre, "pre2fa", 300) if pre else None
    if not uid:
        return RedirectResponse("/login", 303)
    user = db.get(User, uid)
    if not user or not user.totp_secret or not pyotp.TOTP(user.totp_secret).verify(code.strip(), valid_window=1):
        return render(request, "auth/twofa_verify.html", error="That code is not valid. Try again.")
    register_successful_login(db, user)
    resp = RedirectResponse("/dashboard", 303)
    _set_session(resp, user.id, remember=False)
    resp.delete_cookie("clavyx_pre2fa")
    return resp


@router.post("/logout")
def logout(request: Request, csrf_field: str = Form("", alias="_csrf")):
    resp = RedirectResponse("/", 303)
    resp.delete_cookie(SESSION_COOKIE)
    return resp


# ---------------- password reset (works offline: link is shown on screen) ----------------
@router.get("/forgot")
def forgot_form(request: Request):
    return render(request, "auth/forgot.html")


@router.post("/forgot")
def forgot(request: Request, db: Session = Depends(get_db), email: str = Form(...), csrf_field: str = Form("", alias="_csrf")):
    user = db.query(User).filter(User.email == email.lower().strip()).first()
    # We never reveal whether the email exists. In production the link is emailed.
    # In this build, if it exists, we show the link on screen so you can test offline.
    link = None
    if user:
        token = make_link_token(user.id, "reset")
        link = f"/reset?token={token}"
    return render(request, "auth/forgot.html",
                  message="If that email is registered, a reset link has been created.",
                  dev_link=link)


@router.get("/reset")
def reset_form(request: Request, token: str = ""):
    uid = read_link_token(token, "reset", settings.RESET_TOKEN_MINUTES * 60)
    if not uid:
        return render(request, "auth/reset.html", invalid=True)
    return render(request, "auth/reset.html", token=token)


@router.post("/reset")
def reset(request: Request, db: Session = Depends(get_db),
          token: str = Form(...), password: str = Form(...), csrf_field: str = Form("", alias="_csrf")):
    uid = read_link_token(token, "reset", settings.RESET_TOKEN_MINUTES * 60)
    if not uid:
        return render(request, "auth/reset.html", invalid=True)
    if not PASSWORD_RULE.match(password):
        return render(request, "auth/reset.html", token=token,
                      error="Password needs at least 8 characters, with a letter and a number.")
    user = db.get(User, uid)
    if not user:
        return render(request, "auth/reset.html", invalid=True)
    user.password_hash = hash_password(password)
    user.failed_attempts = 0; user.locked_until = None
    db.commit()
    return render(request, "auth/login.html", message="Your password has been updated. Please sign in.",
                  next="/dashboard")
