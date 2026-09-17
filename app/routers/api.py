"""JSON API. The analyzer page calls POST /api/analyze and renders the result
without a full page reload, which gives the app its live, modern feel."""
from __future__ import annotations
import json
from fastapi import APIRouter, Request, Depends, Header
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from pydantic import ValidationError

from ..database import get_db
from ..deps import get_current_user, CSRF_COOKIE
from ..models import Analysis
from ..schemas import AnalyzeIn
from ..config import settings
from ..security import csrf_ok, rate_limit
from ..services import pipeline

router = APIRouter(prefix="/api")


@router.post("/analyze")
def analyze(request: Request, payload: AnalyzeIn = None, db: Session = Depends(get_db),
            x_csrf_token: str | None = Header(default=None)):
    user = get_current_user(request, db)
    if not user:
        return JSONResponse({"error": "Please sign in to analyse an argument."}, status_code=401)
    # CSRF for the JSON API: the token comes in a header set by our own script.
    if not csrf_ok(request.cookies.get(CSRF_COOKIE), x_csrf_token):
        return JSONResponse({"error": "Security token missing or invalid. Refresh and try again."}, status_code=403)
    ip = request.client.host if request.client else "unknown"
    if not rate_limit(f"analyze:{user.id}:{ip}", settings.ANALYZE_LIMIT_PER_MINUTE):
        return JSONResponse({"error": "You are analysing very quickly. Please wait a moment."}, status_code=429)

    try:
        body = payload if payload is not None else AnalyzeIn(**({}))
    except ValidationError as e:
        return JSONResponse({"error": e.errors()[0]["msg"]}, status_code=422)

    result = pipeline.analyse(body.text)
    a = Analysis(user_id=user.id, title=pipeline.suggest_title(body.text),
                 input_text=body.text, result_json=json.dumps(result),
                 robustness=result.get("robustness", 0))
    db.add(a); db.commit(); db.refresh(a)
    result["_id"] = a.id
    return JSONResponse(result)
