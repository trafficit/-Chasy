import datetime as dt
from io import BytesIO
from pathlib import Path

from fastapi import Depends, FastAPI, File, HTTPException, Response, UploadFile
from fastapi.responses import RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from . import models
from .auth import (
    COOKIE,
    current_user,
    hash_token,
    make_session_jwt,
    new_magic_token,
)
from .config import settings
from .db import Base, engine, get_db
from .mail import send_magic_link
from .worklog import build_xlsx, compute, parse_xlsx

Base.metadata.create_all(engine)

app = FastAPI(title="WorkLog")

def _find_frontend() -> Path:
    import os

    here = Path(__file__).resolve()
    candidates = [
        Path(os.environ["FRONTEND_DIR"]) if os.environ.get("FRONTEND_DIR") else None,
        here.parent.parent / "frontend",         # docker image: /app/frontend
        here.parent.parent.parent / "frontend",  # repo: worklog-web/frontend
    ]
    for c in candidates:
        if c and c.is_dir():
            return c
    return here.parent.parent / "frontend"


FRONTEND_DIR = _find_frontend()


# --------------------------------------------------------------------------- #
# schemas
# --------------------------------------------------------------------------- #
class EmailIn(BaseModel):
    email: EmailStr


class EntryIn(BaseModel):
    date: str
    start: str = "00:00"
    end: str = "00:00"
    lunch: str = ""
    comment: str = ""


class EntryOut(BaseModel):
    id: str
    position: int
    date: str
    start: str
    end: str
    duration: str
    lunch: str
    net: str
    comment: str

    model_config = {"from_attributes": True}


class ReorderIn(BaseModel):
    ids: list[str]


# --------------------------------------------------------------------------- #
# auth
# --------------------------------------------------------------------------- #
@app.post("/api/auth/request")
async def auth_request(body: EmailIn, db: Session = Depends(get_db)):
    email = body.email.lower()
    raw, token_hash = new_magic_token()
    db.add(
        models.MagicToken(
            email=email,
            token_hash=token_hash,
            expires_at=dt.datetime.now(dt.timezone.utc)
            + dt.timedelta(minutes=settings.magic_link_ttl_minutes),
        )
    )
    db.commit()
    link = f"{settings.base_url.rstrip('/')}/api/auth/callback?token={raw}"
    await send_magic_link(email, link)
    return {"ok": True}


@app.get("/api/auth/callback")
def auth_callback(token: str, db: Session = Depends(get_db)):
    now = dt.datetime.now(dt.timezone.utc)
    tok = db.scalar(
        select(models.MagicToken).where(
            models.MagicToken.token_hash == hash_token(token),
            models.MagicToken.used.is_(False),
            models.MagicToken.expires_at > now,
        )
    )
    if tok is None:
        return RedirectResponse("/?error=link", status_code=303)

    tok.used = True
    user = db.scalar(select(models.User).where(models.User.email == tok.email))
    if user is None:
        user = models.User(email=tok.email)
        db.add(user)
        db.flush()
    db.commit()

    resp = RedirectResponse("/", status_code=303)
    resp.set_cookie(
        COOKIE,
        make_session_jwt(user.id),
        max_age=settings.session_days * 86400,
        httponly=True,
        samesite="lax",
        secure=settings.base_url.startswith("https"),
    )
    return resp


@app.post("/api/auth/logout")
def logout():
    resp = Response(status_code=204)
    resp.delete_cookie(COOKIE)
    return resp


@app.get("/api/me")
def me(user: models.User = Depends(current_user)):
    return {"email": user.email}


# --------------------------------------------------------------------------- #
# entries
# --------------------------------------------------------------------------- #
def _entries_q(user_id: str):
    return (
        select(models.Entry)
        .where(models.Entry.user_id == user_id)
        .order_by(models.Entry.position, models.Entry.created_at)
    )


@app.get("/api/entries", response_model=list[EntryOut])
def list_entries(user=Depends(current_user), db: Session = Depends(get_db)):
    return db.scalars(_entries_q(user.id)).all()


@app.post("/api/entries", response_model=EntryOut)
def create_entry(
    body: EntryIn, user=Depends(current_user), db: Session = Depends(get_db)
):
    try:
        computed = compute(body.date, body.start, body.end, body.lunch, body.comment)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    max_pos = db.scalar(
        select(func.coalesce(func.max(models.Entry.position), -1)).where(
            models.Entry.user_id == user.id
        )
    )
    entry = models.Entry(user_id=user.id, position=max_pos + 1, **computed)
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


@app.put("/api/entries/{entry_id}", response_model=EntryOut)
def update_entry(
    entry_id: str,
    body: EntryIn,
    user=Depends(current_user),
    db: Session = Depends(get_db),
):
    entry = db.get(models.Entry, entry_id)
    if entry is None or entry.user_id != user.id:
        raise HTTPException(status_code=404, detail="Not found")
    try:
        computed = compute(body.date, body.start, body.end, body.lunch, body.comment)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    for key, value in computed.items():
        setattr(entry, key, value)
    db.commit()
    db.refresh(entry)
    return entry


@app.delete("/api/entries/{entry_id}", status_code=204)
def delete_entry(
    entry_id: str, user=Depends(current_user), db: Session = Depends(get_db)
):
    entry = db.get(models.Entry, entry_id)
    if entry is None or entry.user_id != user.id:
        raise HTTPException(status_code=404, detail="Not found")
    db.delete(entry)
    db.commit()
    return Response(status_code=204)


@app.post("/api/entries/reorder")
def reorder(
    body: ReorderIn, user=Depends(current_user), db: Session = Depends(get_db)
):
    rows = {e.id: e for e in db.scalars(_entries_q(user.id)).all()}
    for pos, entry_id in enumerate(body.ids):
        if entry_id in rows:
            rows[entry_id].position = pos
    db.commit()
    return {"ok": True}


# --------------------------------------------------------------------------- #
# excel
# --------------------------------------------------------------------------- #
@app.get("/api/export.xlsx")
def export_xlsx(user=Depends(current_user), db: Session = Depends(get_db)):
    rows = db.scalars(_entries_q(user.id)).all()
    data = build_xlsx(rows)
    filename = f"worklog_{dt.date.today().isoformat()}.xlsx"
    return StreamingResponse(
        BytesIO(data),
        media_type=(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ),
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.post("/api/import")
async def import_xlsx(
    file: UploadFile = File(...),
    user=Depends(current_user),
    db: Session = Depends(get_db),
):
    raw = await file.read()
    try:
        parsed = parse_xlsx(raw)
    except Exception as exc:  # noqa: BLE001 - surface a readable message
        raise HTTPException(status_code=400, detail=f"Cannot read file: {exc}")

    db.query(models.Entry).filter(models.Entry.user_id == user.id).delete(
        synchronize_session=False
    )
    for pos, row in enumerate(parsed):
        try:
            computed = compute(
                row["date"], row["start"], row["end"], row["lunch"], row["comment"]
            )
        except ValueError:
            computed = {
                "date": row["date"],
                "start": row["start"],
                "end": row["end"],
                "duration": "0:00",
                "lunch": "",
                "net": "0:00",
                "comment": row["comment"],
            }
        db.add(models.Entry(user_id=user.id, position=pos, **computed))
    db.commit()
    return {"imported": len(parsed)}


# --------------------------------------------------------------------------- #
# static frontend (mounted last so /api/* wins)
# --------------------------------------------------------------------------- #
app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
