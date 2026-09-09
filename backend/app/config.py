from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)

    # storage
    database_url: str = "postgresql+psycopg2://worklog:worklog@db:5432/worklog"

    # security / session
    secret_key: str = "change-me-please"
    base_url: str = "http://localhost:8000"
    session_days: int = 30
    magic_link_ttl_minutes: int = 20

    # e-mail (magic link)
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "Chasy <no-reply@example.com>"
    smtp_starttls: bool = True

    # if true (or SMTP not configured) the magic link is also printed to the log
    dev_echo_magic_link: bool = False

    # anti-abuse for POST /api/auth/request (magic-link spam / e-mail bombing)
    auth_min_interval_sec: int = 30       # min seconds between links for one e-mail
    auth_max_live_tokens: int = 3         # max unused, unexpired links per e-mail
    auth_max_per_min_per_ip: int = 5
    auth_max_per_hour_per_ip: int = 20
    # honeypot form field name; a request that fills it is silently ignored
    honeypot_field: str = "website"

    # licensing (model A: access codes with expiry)
    # empty -> licensing disabled, everyone can use the app freely
    license_required: bool = False
    # credentials for the /admin panel; empty admin_token -> panel disabled.
    # admin_user is optional: set it to also require a login name.
    admin_user: str = ""
    admin_token: str = ""
    # free trial (days) granted to a brand-new account before a code is needed;
    # 0 -> no trial, a code is required immediately
    trial_days: int = 0
    # comma-separated e-mail domains that are always free (no code, no banner),
    # e.g. "ges-rent.sk,example.com"
    free_email_domains: str = ""
    # comma-separated codes that are always valid: seeded on startup as
    # never-expiring, unlimited-seat licenses. e.g. "MayDay2027"
    promo_codes: str = ""
    # bump when the /terms text changes; stored per user on acceptance
    tos_version: str = "2026-09-09"

    # ---- pricing / invoices ----
    invoice_price: str = "7"          # per company per month
    invoice_currency: str = "EUR"
    invoice_due_days: int = 7
    invoice_number_prefix: str = "PF"  # proforma
    # seller block printed on the invoice. If name or IBAN is empty, the
    # "create invoice" button is hidden and only the price is shown.
    seller_name: str = ""
    seller_address: str = ""
    seller_reg_id: str = ""           # IČO / рег. номер (не НДС)
    seller_iban: str = ""
    seller_bank: str = ""
    seller_email: str = ""
    # optional Wise / other payment link shown on the invoice; if set you can
    # leave SELLER_IBAN empty and the IBAN never appears
    seller_pay_link: str = ""
    # printed on every invoice — the app is built for non-VAT sellers
    invoice_note: str = "Nie sme platcami DPH. / Не является плательщиком НДС."


settings = Settings()

