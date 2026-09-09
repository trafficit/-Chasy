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
    seller_reg_id: str = ""           # IČO / рег. номер
    seller_vat_id: str = ""           # DIČ / IČ DPH (empty if not a VAT payer)
    seller_iban: str = ""
    seller_bank: str = ""
    seller_email: str = ""
    invoice_note: str = "Nie sme platcami DPH."


settings = Settings()

