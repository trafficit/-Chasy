import datetime as dt
import secrets
from io import BytesIO
from pathlib import Path

from fastapi import Depends, FastAPI, File, Header, HTTPException, Response, UploadFile
from fastapi.responses import FileResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from . import invoice as inv
from . import license as lic
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


def _migrate() -> None:
    """Idempotent tweaks for databases created before licensing existed."""
    with engine.begin() as conn:
        conn.execute(
            text("ALTER TABLE users ADD COLUMN IF NOT EXISTS license_id VARCHAR")
        )
        conn.execute(
            text(
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS "
                "tos_accepted_at TIMESTAMPTZ"
            )
        )
        conn.execute(
            text(
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS "
                "tos_version VARCHAR DEFAULT ''"
            )
        )
        conn.execute(
            text("ALTER TABLE invoices DROP COLUMN IF EXISTS buyer_vat_id")
        )


def _seed_promo_codes() -> None:
    """Codes listed in PROMO_CODES always exist as never-expiring free licenses."""
    from sqlalchemy import func as _func
    from sqlalchemy.orm import Session as _Session

    codes = lic.promo_codes()
    if not codes:
        return
    with _Session(engine) as db:
        for code in codes:
            row = db.scalar(
                select(models.License).where(
                    _func.upper(models.License.code) == code.upper()
                )
            )
            if row is None:
                db.add(
                    models.License(
                        code=code,
                        company="(promo)",
                        valid_until=None,
                        seats=None,
                        active=True,
                        note="promo code (PROMO_CODES)",
                    )
                )
            else:
                row.active = True
                row.valid_until = None
        db.commit()


_migrate()
_seed_promo_codes()

app = FastAPI(title="Chasy")

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


class RedeemIn(BaseModel):
    code: str
    accept_terms: bool = False


class LicenseIn(BaseModel):
    company: str = ""
    code: str = ""  # empty -> auto-generate CHASY-XXXX-XXXX
    valid_until: dt.date | None = None
    seats: int | None = None
    note: str = ""


class LicensePatch(BaseModel):
    company: str | None = None
    valid_until: dt.date | None = None
    clear_valid_until: bool = False
    seats: int | None = None
    clear_seats: bool = False
    active: bool | None = None
    note: str | None = None


class InvoiceIn(BaseModel):
    buyer_name: str
    buyer_reg_id: str = ""
    buyer_address: str = ""
    months: int = 1


# --------------------------------------------------------------------------- #
# access control
# --------------------------------------------------------------------------- #
def require_writable(user: models.User = Depends(current_user)) -> models.User:
    if not lic.can_write(user):
        raise HTTPException(
            status_code=402,
            detail="An active access code is required.",
        )
    return user


def require_admin(
    x_admin_token: str = Header(default=""),
    x_admin_user: str = Header(default=""),
) -> None:
    if not settings.admin_token:
        raise HTTPException(status_code=404, detail="Admin panel is disabled.")
    ok = secrets.compare_digest(x_admin_token, settings.admin_token)
    if settings.admin_user:
        ok = ok and secrets.compare_digest(x_admin_user, settings.admin_user)
    if not ok:
        raise HTTPException(status_code=401, detail="Bad admin credentials.")


def _license_public(lc: models.License, users_count: int) -> dict:
    return {
        "id": lc.id,
        "code": lc.code,
        "company": lc.company,
        "valid_until": lc.valid_until.date().isoformat() if lc.valid_until else None,
        "seats": lc.seats,
        "active": lc.active,
        "note": lc.note,
        "users": users_count,
        "created_at": lc.created_at.isoformat(),
    }


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
    return {"email": user.email, "license": lic.license_state(user)}


# --------------------------------------------------------------------------- #
# licensing (model A: access codes)
# --------------------------------------------------------------------------- #
@app.post("/api/license/redeem")
def redeem(
    body: RedeemIn,
    user: models.User = Depends(current_user),
    db: Session = Depends(get_db),
):
    if not body.accept_terms:
        raise HTTPException(status_code=400, detail="terms_not_accepted")

    code = body.code.strip()
    lc = db.scalar(
        select(models.License).where(func.upper(models.License.code) == code.upper())
    )
    if lc is None:
        raise HTTPException(status_code=404, detail="unknown_code")
    if not lc.active:
        raise HTTPException(status_code=403, detail="revoked_code")
    valid_until = lc.valid_until
    if valid_until is not None and valid_until.tzinfo is None:
        valid_until = valid_until.replace(tzinfo=dt.timezone.utc)
    if valid_until is not None and valid_until < dt.datetime.now(dt.timezone.utc):
        raise HTTPException(status_code=403, detail="expired_code")

    if lc.seats is not None and user.license_id != lc.id:
        taken = db.scalar(
            select(func.count(models.User.id)).where(models.User.license_id == lc.id)
        )
        if taken >= lc.seats:
            raise HTTPException(status_code=403, detail="seats_full")

    user.license_id = lc.id
    user.tos_accepted_at = dt.datetime.now(dt.timezone.utc)
    user.tos_version = settings.tos_version
    db.commit()
    db.refresh(user)
    return {"license": lic.license_state(user)}


# --------------------------------------------------------------------------- #
# pricing + proforma invoices
# --------------------------------------------------------------------------- #
@app.get("/api/info")
def public_info():
    return {
        "price": settings.invoice_price,
        "currency": settings.invoice_currency.upper(),
        "currency_sign": inv.currency_sign(),
        "invoice_enabled": inv.enabled(),
    }


def _invoice_public(row: models.Invoice) -> dict:
    return {
        "number": row.number,
        "variable_symbol": row.variable_symbol,
        "status": row.status,
        "issued_on": row.issued_on.date().isoformat(),
        "due_on": row.due_on.date().isoformat() if row.due_on else None,
        "buyer": {
            "name": row.buyer_name,
            "reg_id": row.buyer_reg_id,
            "address": row.buyer_address,
            "email": row.user_email,
        },
        "months": row.months,
        "unit_price": row.unit_price,
        "amount": row.amount,
        "currency": row.currency,
        "seller": inv.seller_block(),
        "note": settings.invoice_note,
        "product": "Chasy — доступ к сервису",
    }


@app.post("/api/invoice")
def create_invoice(
    body: InvoiceIn,
    user: models.User = Depends(current_user),
    db: Session = Depends(get_db),
):
    if not inv.enabled():
        raise HTTPException(status_code=404, detail="invoicing_disabled")
    if not body.buyer_name.strip():
        raise HTTPException(status_code=400, detail="buyer_name_required")

    calc = inv.compute(body.months)
    now = dt.datetime.now(dt.timezone.utc)
    with engine.begin() as conn:
        number, vs = inv.next_number(conn)

    row = models.Invoice(
        number=number,
        variable_symbol=vs,
        user_id=user.id,
        user_email=user.email,
        buyer_name=body.buyer_name.strip(),
        buyer_reg_id=body.buyer_reg_id.strip(),
        buyer_address=body.buyer_address.strip(),
        months=calc["months"],
        unit_price=calc["unit_price"],
        amount=calc["amount"],
        currency=calc["currency"],
        issued_on=now,
        due_on=now + dt.timedelta(days=settings.invoice_due_days),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _invoice_public(row)


@app.get("/api/invoice/{number}")
def get_invoice(
    number: str,
    user: models.User = Depends(current_user),
    db: Session = Depends(get_db),
):
    row = db.scalar(select(models.Invoice).where(models.Invoice.number == number))
    if row is None or row.user_id != user.id:
        raise HTTPException(status_code=404, detail="not_found")
    return _invoice_public(row)


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
    body: EntryIn, user=Depends(require_writable), db: Session = Depends(get_db)
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
    user=Depends(require_writable),
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
    entry_id: str, user=Depends(require_writable), db: Session = Depends(get_db)
):
    entry = db.get(models.Entry, entry_id)
    if entry is None or entry.user_id != user.id:
        raise HTTPException(status_code=404, detail="Not found")
    db.delete(entry)
    db.commit()
    return Response(status_code=204)


@app.post("/api/entries/reorder")
def reorder(
    body: ReorderIn, user=Depends(require_writable), db: Session = Depends(get_db)
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
    filename = f"chasy_{dt.date.today().isoformat()}.xlsx"
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
    user=Depends(require_writable),
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
# admin panel (X-Admin-Token header == ADMIN_TOKEN)
# --------------------------------------------------------------------------- #
def _users_count(db: Session, license_id: str) -> int:
    return db.scalar(
        select(func.count(models.User.id)).where(models.User.license_id == license_id)
    )


@app.get("/api/admin/licenses", dependencies=[Depends(require_admin)])
def admin_list_licenses(db: Session = Depends(get_db)):
    rows = db.scalars(
        select(models.License).order_by(models.License.created_at.desc())
    ).all()
    return [_license_public(lc, _users_count(db, lc.id)) for lc in rows]


@app.post("/api/admin/licenses", dependencies=[Depends(require_admin)])
def admin_create_license(body: LicenseIn, db: Session = Depends(get_db)):
    def taken(candidate: str) -> bool:
        return bool(
            db.scalar(
                select(models.License).where(
                    func.upper(models.License.code) == candidate.upper()
                )
            )
        )

    custom = body.code.strip()
    if custom:
        if len(custom) < 4:
            raise HTTPException(status_code=400, detail="code too short")
        if taken(custom):
            raise HTTPException(status_code=409, detail="code already exists")
        code = custom
    else:
        for _ in range(5):
            code = lic.generate_code()
            if not taken(code):
                break
        else:
            raise HTTPException(status_code=500, detail="could not allocate a code")

    vu = (
        dt.datetime.combine(body.valid_until, dt.time.max, tzinfo=dt.timezone.utc)
        if body.valid_until
        else None
    )
    lc = models.License(
        code=code,
        company=body.company.strip(),
        valid_until=vu,
        seats=body.seats,
        note=body.note.strip(),
    )
    db.add(lc)
    db.commit()
    db.refresh(lc)
    return _license_public(lc, 0)


@app.patch("/api/admin/licenses/{license_id}", dependencies=[Depends(require_admin)])
def admin_update_license(
    license_id: str, body: LicensePatch, db: Session = Depends(get_db)
):
    lc = db.get(models.License, license_id)
    if lc is None:
        raise HTTPException(status_code=404, detail="not found")
    if body.company is not None:
        lc.company = body.company.strip()
    if body.note is not None:
        lc.note = body.note.strip()
    if body.active is not None:
        lc.active = body.active
    if body.clear_valid_until:
        lc.valid_until = None
    elif body.valid_until is not None:
        lc.valid_until = dt.datetime.combine(
            body.valid_until, dt.time.max, tzinfo=dt.timezone.utc
        )
    if body.clear_seats:
        lc.seats = None
    elif body.seats is not None:
        lc.seats = body.seats
    db.commit()
    db.refresh(lc)
    return _license_public(lc, _users_count(db, lc.id))


@app.delete(
    "/api/admin/licenses/{license_id}",
    status_code=204,
    dependencies=[Depends(require_admin)],
)
def admin_delete_license(license_id: str, db: Session = Depends(get_db)):
    lc = db.get(models.License, license_id)
    if lc is not None:
        db.execute(
            text("UPDATE users SET license_id = NULL WHERE license_id = :i"),
            {"i": license_id},
        )
        db.delete(lc)
        db.commit()
    return Response(status_code=204)


@app.get("/api/admin/users", dependencies=[Depends(require_admin)])
def admin_list_users(db: Session = Depends(get_db)):
    rows = db.scalars(
        select(models.User).order_by(models.User.created_at.desc())
    ).all()
    return [
        {
            "id": u.id,
            "email": u.email,
            "created_at": u.created_at.isoformat(),
            "license_code": u.license.code if u.license else None,
            "license_company": u.license.company if u.license else None,
        }
        for u in rows
    ]


@app.post(
    "/api/admin/users/{user_id}/unbind",
    status_code=204,
    dependencies=[Depends(require_admin)],
)
def admin_unbind_user(user_id: str, db: Session = Depends(get_db)):
    u = db.get(models.User, user_id)
    if u is not None:
        u.license_id = None
        db.commit()
    return Response(status_code=204)


@app.get("/api/admin/invoices", dependencies=[Depends(require_admin)])
def admin_list_invoices(db: Session = Depends(get_db)):
    rows = db.scalars(
        select(models.Invoice).order_by(models.Invoice.created_at.desc())
    ).all()
    return [
        {
            "number": r.number,
            "variable_symbol": r.variable_symbol,
            "user_email": r.user_email,
            "buyer_name": r.buyer_name,
            "months": r.months,
            "amount": r.amount,
            "currency": r.currency,
            "status": r.status,
            "issued_on": r.issued_on.date().isoformat(),
            "due_on": r.due_on.date().isoformat() if r.due_on else None,
        }
        for r in rows
    ]


@app.get("/admin")
def admin_page():
    return FileResponse(FRONTEND_DIR / "admin.html")


@app.get("/terms")
def terms_page():
    return FileResponse(FRONTEND_DIR / "terms.html")


@app.get("/invoice")
def invoice_page():
    return FileResponse(FRONTEND_DIR / "invoice.html")


# --------------------------------------------------------------------------- #
# static frontend (mounted last so /api/* wins)
# --------------------------------------------------------------------------- #
app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
