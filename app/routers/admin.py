"""A small admin area, visible only to users whose role is 'admin'.
Make yourself an admin once with the helper script: python make_admin.py you@email"""
from __future__ import annotations
from fastapi import APIRouter, Request, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from ..database import get_db
from ..deps import render, require_user
from ..models import User, Analysis

router = APIRouter()


@router.get("/admin")
def admin_home(request: Request, db: Session = Depends(get_db), user: User = Depends(require_user)):
    if user.role != "admin":
        return render(request, "errors/404.html", user=user, status_code=404)
    users = db.query(User).order_by(User.created_at.desc()).all()
    total_analyses = db.query(func.count(Analysis.id)).scalar() or 0
    avg = db.query(func.avg(Analysis.robustness)).scalar()
    return render(request, "admin/dashboard.html", user=user, active="admin",
                  users=users, total_analyses=total_analyses,
                  avg=round(avg) if avg else 0)
