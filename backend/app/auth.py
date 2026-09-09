import datetime as dt
import hashlib
import secrets

from fastapi import Depends, HTTPException, Request
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from . import models
from .config import settings
from .db import get_db

ALGO = "HS256"
COOKIE = "worklog_session"


def hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def new_magic_token() -> tuple[str, str]:
    raw = secrets.token_urlsafe(32)
    return raw, hash_token(raw)


def make_session_jwt(user_id: str) -> str:
    now = dt.datetime.now(dt.timezone.utc)
    payload = {
        "sub": user_id,
        "iat": now,
        "exp": now + dt.timedelta(days=settings.session_days),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=ALGO)


def current_user(
    request: Request, db: Session = Depends(get_db)
) -> models.User:
    token = request.cookies.get(COOKIE)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGO])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid session")
    user = db.get(models.User, payload.get("sub"))
    if user is None:
        raise HTTPException(status_code=401, detail="Unknown user")
    return user
