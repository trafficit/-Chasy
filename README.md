# Chasy — веб-версия

Онлайн-версия десктопного WorkLog Dashboard: учёт рабочих часов с доступом
с телефона и общим хранением. Вход по ссылке из письма (magic link),
у каждого сотрудника свой лог, экспорт/импорт `.xlsx` как в десктопной версии.

## Стек

| | |
|---|---|
| Фронтенд | статичный PWA (ванильный JS), ставится на телефон «на главный экран», работает офлайн для просмотра |
| Бэкенд | FastAPI + SQLAlchemy, вся арифметика времени и Excel портированы из `worklog_dashboard2.py` |
| БД | PostgreSQL |
| Вход | magic link по e-mail, сессия в httpOnly-cookie (JWT) |
| Прокси/TLS | Caddy (автоматический Let's Encrypt) |

Всё поднимается одним `docker compose up`.

## Быстрый старт на VPS

```bash
git clone https://github.com/trafficit/-Chasy.git worklog
cd worklog
cp .env.example .env
nano .env            # заполнить домен, секреты, SMTP
docker compose up -d --build
```

Открыть `https://<домен>` → ввести почту → перейти по ссылке из письма.

### Что заполнить в `.env`

| Переменная | Что это |
|---|---|
| `SITE_ADDRESS` | домен для Caddy, напр. `worklog.example.com` (или `:80` для локального теста) |
| `BASE_URL` | публичный адрес, как его открывают пользователи, напр. `https://worklog.example.com` — попадает в ссылки из писем |
| `SECRET_KEY` | `openssl rand -hex 32` |
| `POSTGRES_PASSWORD` | длинный случайный пароль |
| `SMTP_*` | доступ к почтовому серверу для отправки писем. Пусто → ссылка печатается в `docker compose logs -f app` (годится для первого теста) |

DNS: A-запись поддомена → IP VPS. Порты 80 и 443 должны быть открыты.

## Локальный тест без домена и почты

```bash
cp .env.example .env
# в .env:  SITE_ADDRESS=:80   BASE_URL=http://localhost   DEV_ECHO_MAGIC_LINK=true
docker compose up --build
# открыть http://localhost , запросить вход, ссылку взять из логов app
```

## Обновление

```bash
git pull && docker compose up -d --build
```

Данные (Postgres, сертификаты) лежат в docker volume и переживают пересборку.

## API (для справки)

| Метод | Путь | |
|---|---|---|
| POST | `/api/auth/request` | `{email}` → отправить ссылку |
| GET | `/api/auth/callback?token=` | вход, ставит cookie |
| POST | `/api/auth/logout` | выход |
| GET | `/api/me` | текущий пользователь |
| GET/POST | `/api/entries` | список / создать |
| PUT/DELETE | `/api/entries/{id}` | изменить / удалить |
| POST | `/api/entries/reorder` | `{ids:[...]}` порядок |
| GET | `/api/export.xlsx` | выгрузка Excel |
| POST | `/api/import` | загрузка Excel (заменяет записи) |
