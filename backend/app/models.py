import datetime as dt
import uuid

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(String, unique=True, index=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_now)
    license_id: Mapped[str | None] = mapped_column(
        ForeignKey("licenses.id", ondelete="SET NULL"), nullable=True, index=True
    )
    license: Mapped["License | None"] = relationship(lazy="joined")
    tos_accepted_at: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    tos_version: Mapped[str] = mapped_column(String, default="")


class License(Base):
    __tablename__ = "licenses"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    code: Mapped[str] = mapped_column(String, unique=True, index=True)
    company: Mapped[str] = mapped_column(String, default="")
    # NULL -> never expires
    valid_until: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # NULL -> unlimited seats
    seats: Mapped[int | None] = mapped_column(Integer, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_now)


class MagicToken(Base):
    __tablename__ = "magic_tokens"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(String, index=True)
    token_hash: Mapped[str] = mapped_column(String, index=True)
    expires_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True))
    used: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Invoice(Base):
    __tablename__ = "invoices"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    number: Mapped[str] = mapped_column(String, unique=True, index=True)
    variable_symbol: Mapped[str] = mapped_column(String, default="")
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    user_email: Mapped[str] = mapped_column(String, default="")
    buyer_name: Mapped[str] = mapped_column(String, default="")
    buyer_reg_id: Mapped[str] = mapped_column(String, default="")
    buyer_vat_id: Mapped[str] = mapped_column(String, default="")
    buyer_address: Mapped[str] = mapped_column(Text, default="")
    months: Mapped[int] = mapped_column(Integer, default=1)
    unit_price: Mapped[str] = mapped_column(String, default="")
    amount: Mapped[str] = mapped_column(String, default="")
    currency: Mapped[str] = mapped_column(String, default="EUR")
    status: Mapped[str] = mapped_column(String, default="proforma")
    issued_on: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), default=_now
    )
    due_on: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Entry(Base):
    __tablename__ = "entries"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    position: Mapped[int] = mapped_column(Integer, default=0)
    date: Mapped[str] = mapped_column(String)
    start: Mapped[str] = mapped_column(String)
    end: Mapped[str] = mapped_column(String)
    duration: Mapped[str] = mapped_column(String)
    lunch: Mapped[str] = mapped_column(String, default="")
    net: Mapped[str] = mapped_column(String)
    comment: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_now)
