"""Public marketing and information pages."""
from __future__ import annotations
from fastapi import APIRouter, Request, Depends
from sqlalchemy.orm import Session
from ..deps import render, get_current_user
from ..database import get_db

router = APIRouter()


def _u(request, db):
    return get_current_user(request, db)


@router.get("/")
def home(request: Request, db: Session = Depends(get_db)):
    return render(request, "index.html", user=_u(request, db), active="home")


@router.get("/how-it-works")
def how(request: Request, db: Session = Depends(get_db)):
    return render(request, "how_it_works.html", user=_u(request, db), active="how")


@router.get("/learn")
def learn(request: Request, db: Session = Depends(get_db)):
    return render(request, "learn.html", user=_u(request, db), active="learn")


@router.get("/pricing")
def pricing(request: Request, db: Session = Depends(get_db)):
    return render(request, "pricing.html", user=_u(request, db), active="pricing")


@router.get("/about")
def about(request: Request, db: Session = Depends(get_db)):
    return render(request, "about.html", user=_u(request, db), active="about")


@router.get("/terms")
def terms(request: Request, db: Session = Depends(get_db)):
    return render(request, "terms.html", user=_u(request, db))


@router.get("/privacy")
def privacy(request: Request, db: Session = Depends(get_db)):
    return render(request, "privacy.html", user=_u(request, db))
