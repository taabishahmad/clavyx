"""Signed-in application pages: dashboard, analyzer, result, history, settings."""
from __future__ import annotations
import json
import pyotp
from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import render, require_user, CSRF_COOKIE
from ..models import User, Analysis
from ..config import settings
from ..security import csrf_ok, hash_password, verify_password, PASSWORD_RULE
from ..services import llm_provider

router = APIRouter()


def _csrf_ok(request, sent):
    return csrf_ok(request.cookies.get(CSRF_COOKIE), sent)


@router.get("/dashboard")
def dashboard(request: Request, db: Session = Depends(get_db), user: User = Depends(require_user)):
    recent = (db.query(Analysis).filter(Analysis.user_id == user.id)
              .order_by(Analysis.created_at.desc()).limit(5).all())
    total = db.query(Analysis).filter(Analysis.user_id == user.id).count()
    avg = 0
    if total:
        avg = round(sum(a.robustness for a in db.query(Analysis)
                        .filter(Analysis.user_id == user.id).all()) / total)
    return render(request, "app/dashboard.html", user=user, active="dashboard",
                  recent=recent, total=total, avg=avg, provider=llm_provider.active_provider())


@router.get("/analyze")
def analyzer(request: Request, db: Session = Depends(get_db), user: User = Depends(require_user)):
    return render(request, "app/analyzer.html", user=user, active="analyze",
                  provider=llm_provider.active_provider())


@router.get("/analysis/{analysis_id}")
def view_analysis(analysis_id: int, request: Request, db: Session = Depends(get_db),
                  user: User = Depends(require_user)):
    a = db.get(Analysis, analysis_id)
    if not a or a.user_id != user.id:
        return render(request, "errors/404.html", user=user, status_code=404)
    result = json.loads(a.result_json)
    return render(request, "app/result.html", user=user, active="history",
                  analysis=a, result=result, result_json=a.result_json)


@router.get("/history")
def history(request: Request, db: Session = Depends(get_db), user: User = Depends(require_user)):
    items = (db.query(Analysis).filter(Analysis.user_id == user.id)
             .order_by(Analysis.created_at.desc()).all())
    return render(request, "app/history.html", user=user, active="history", items=items)


@router.post("/analysis/{analysis_id}/delete")
def delete_analysis(analysis_id: int, request: Request, db: Session = Depends(get_db),
                    user: User = Depends(require_user), csrf_field: str = Form("", alias="_csrf")):
    if not _csrf_ok(request, csrf_field):
        return RedirectResponse("/history", 303)
    a = db.get(Analysis, analysis_id)
    if a and a.user_id == user.id:
        db.delete(a); db.commit()
    return RedirectResponse("/history", 303)


# ---------------- settings ----------------
@router.get("/settings")
def settings_page(request: Request, db: Session = Depends(get_db), user: User = Depends(require_user)):
    return render(request, "app/settings.html", user=user, active="settings")


@router.post("/settings/profile")
def update_profile(request: Request, db: Session = Depends(get_db), user: User = Depends(require_user),
                   display_name: str = Form(...), csrf_field: str = Form("", alias="_csrf")):
    if not _csrf_ok(request, csrf_field):
        return RedirectResponse("/settings", 303)
    name = display_name.strip()
    if 2 <= len(name) <= 120:
        user.display_name = name; db.commit()
    return render(request, "app/settings.html", user=user, active="settings",
                  message="Profile updated.")


@router.post("/settings/password")
def change_password(request: Request, db: Session = Depends(get_db), user: User = Depends(require_user),
                    current: str = Form(...), new: str = Form(...), csrf_field: str = Form("", alias="_csrf")):
    if not _csrf_ok(request, csrf_field):
        return RedirectResponse("/settings", 303)
    if not verify_password(current, user.password_hash):
        return render(request, "app/settings.html", user=user, active="settings",
                      error="Your current password is incorrect.")
    if not PASSWORD_RULE.match(new):
        return render(request, "app/settings.html", user=user, active="settings",
                      error="New password needs at least 8 characters, with a letter and a number.")
    user.password_hash = hash_password(new); db.commit()
    return render(request, "app/settings.html", user=user, active="settings",
                  message="Password changed.")


@router.post("/settings/2fa/enable")
def enable_2fa(request: Request, db: Session = Depends(get_db), user: User = Depends(require_user),
               csrf_field: str = Form("", alias="_csrf")):
    if not _csrf_ok(request, csrf_field):
        return RedirectResponse("/settings", 303)
    secret = pyotp.random_base32()
    user.totp_secret = secret  # confirmed on first successful verify below
    db.commit()
    uri = pyotp.TOTP(secret).provisioning_uri(name=user.email, issuer_name="CLAVYX")
    return render(request, "app/settings.html", user=user, active="settings",
                  twofa_secret=secret, twofa_uri=uri, message="Scan the code, then enter a code to confirm.")


@router.post("/settings/2fa/confirm")
def confirm_2fa(request: Request, db: Session = Depends(get_db), user: User = Depends(require_user),
                code: str = Form(...), csrf_field: str = Form("", alias="_csrf")):
    if not _csrf_ok(request, csrf_field):
        return RedirectResponse("/settings", 303)
    if user.totp_secret and pyotp.TOTP(user.totp_secret).verify(code.strip(), valid_window=1):
        user.twofa_enabled = True; db.commit()
        return render(request, "app/settings.html", user=user, active="settings",
                      message="Two factor authentication is now on.")
    return render(request, "app/settings.html", user=user, active="settings",
                  error="That code did not match. Two factor was not enabled.")


@router.post("/settings/2fa/disable")
def disable_2fa(request: Request, db: Session = Depends(get_db), user: User = Depends(require_user),
                csrf_field: str = Form("", alias="_csrf")):
    if not _csrf_ok(request, csrf_field):
        return RedirectResponse("/settings", 303)
    user.twofa_enabled = False; user.totp_secret = None; db.commit()
    return render(request, "app/settings.html", user=user, active="settings",
                  message="Two factor authentication is now off.")


@router.post("/settings/delete")
def delete_account(request: Request, db: Session = Depends(get_db), user: User = Depends(require_user),
                   csrf_field: str = Form("", alias="_csrf")):
    if not _csrf_ok(request, csrf_field):
        return RedirectResponse("/settings", 303)
    db.delete(user); db.commit()  # cascade removes their analyses
    resp = RedirectResponse("/", 303)
    resp.delete_cookie("clavyx_session")
    return resp
