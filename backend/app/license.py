"""Model-A licensing: access codes with an expiry date.

Status values returned to the client:
  disabled  - licensing is turned off (LICENSE_REQUIRED=false)
  active    - the user may use every feature
  trial     - inside the free trial window; same as active, carries `trial_until`
  none      - no code redeemed yet and trial is over/absent
  expired   - the redeemed code's valid_until is in the past
  revoked   - the redeemed code was switched off by an admin
"""

import datetime as dt
import secrets

from . import models
from .config import settings

_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no 0/O/1/I


def _now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def generate_code() -> str:
    def block() -> str:
        return "".join(secrets.choice(_ALPHABET) for _ in range(4))

    return f"CHASY-{block()}-{block()}"


def _csv(value: str) -> list[str]:
    return [x.strip() for x in value.split(",") if x.strip()]


def free_domains() -> set[str]:
    return {d.lower().lstrip("@") for d in _csv(settings.free_email_domains)}


def promo_codes() -> list[str]:
    return _csv(settings.promo_codes)


def email_is_free(email: str) -> bool:
    domain = email.rsplit("@", 1)[-1].lower() if "@" in email else ""
    return bool(domain) and domain in free_domains()


def _as_aware(value: dt.datetime | None) -> dt.datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=dt.timezone.utc)
    return value


def license_state(user: models.User) -> dict:
    """Return {status, valid_until?, trial_until?, company?} for this user."""
    if not settings.license_required:
        return {"status": "disabled"}

    if email_is_free(user.email):
        return {"status": "active", "via": "domain"}

    lic = user.license
    if lic is not None:
        valid_until = _as_aware(lic.valid_until)
        if not lic.active:
            return {"status": "revoked", "company": lic.company}
        if valid_until is not None and valid_until < _now():
            return {
                "status": "expired",
                "valid_until": valid_until.isoformat(),
                "company": lic.company,
            }
        out = {"status": "active", "company": lic.company}
        if valid_until is not None:
            out["valid_until"] = valid_until.isoformat()
        return out

    if settings.trial_days > 0:
        trial_until = _as_aware(user.created_at) + dt.timedelta(days=settings.trial_days)
        if trial_until > _now():
            return {"status": "trial", "trial_until": trial_until.isoformat()}

    return {"status": "none"}


def can_write(user: models.User) -> bool:
    return license_state(user)["status"] in ("disabled", "active", "trial")
