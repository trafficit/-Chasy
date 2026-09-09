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
    # token that unlocks the /admin panel; empty -> admin panel disabled
    admin_token: str = ""
    # free trial (days) granted to a brand-new account before a code is needed;
    # 0 -> no trial, a code is required immediately
    trial_days: int = 0


settings = Settings()
