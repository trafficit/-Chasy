"""Proforma-invoice helpers (model A: manual sale, bank transfer / Wise)."""

import datetime as dt
from decimal import Decimal, InvalidOperation

from sqlalchemy import text
from sqlalchemy.engine import Connection

from .config import settings

CURRENCY_SIGN = {"EUR": "€", "USD": "$", "GBP": "£", "CZK": "Kč", "PLN": "zł"}


def enabled() -> bool:
    return bool(settings.seller_name.strip() and settings.seller_iban.strip())


def price_decimal() -> Decimal:
    try:
        return Decimal(str(settings.invoice_price).replace(",", ".").strip())
    except (InvalidOperation, AttributeError):
        return Decimal("0")


def money(value: Decimal) -> str:
    return f"{value:.2f}"


def currency_sign() -> str:
    return CURRENCY_SIGN.get(settings.invoice_currency.upper(), settings.invoice_currency)


def seller_block() -> dict:
    return {
        "name": settings.seller_name,
        "address": settings.seller_address,
        "reg_id": settings.seller_reg_id,
        "iban": settings.seller_iban,
        "bank": settings.seller_bank,
        "email": settings.seller_email or settings.smtp_from,
    }


def next_number(conn: Connection) -> tuple[str, str]:
    """Return (invoice_number, variable_symbol) using a DB sequence."""
    conn.execute(text("CREATE SEQUENCE IF NOT EXISTS invoice_seq START 1"))
    n = conn.execute(text("SELECT nextval('invoice_seq')")).scalar_one()
    year = dt.date.today().year
    seq = f"{year}{int(n):04d}"
    return f"{settings.invoice_number_prefix}{seq}", seq


def compute(months: int) -> dict:
    months = max(1, int(months))
    unit = price_decimal()
    total = unit * months
    return {
        "months": months,
        "unit_price": money(unit),
        "amount": money(total),
        "currency": settings.invoice_currency.upper(),
    }
