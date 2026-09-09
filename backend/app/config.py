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
    smtp_from: str = "Worklog <no-reply@example.com>"
    smtp_starttls: bool = True

    # if true (or SMTP not configured) the magic link is also printed to the log
    dev_echo_magic_link: bool = False


settings = Settings()
