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
| Прокси/TLS | внешний (существующий Caddy на сервере) |

`docker compose` поднимает только `app` + `db`. Приложение слушает
`127.0.0.1:${APP_PORT}`; TLS и домен даёт внешний reverse-proxy.

## Деплой на VPS (за существующим Caddy, домен через Cloudflare)

```bash
git clone https://github.com/trafficit/-Chasy.git ~/Chasy
cd ~/Chasy
cp .env.example .env
nano .env            # BASE_URL, APP_PORT, SECRET_KEY, POSTGRES_PASSWORD, SMTP, ADMIN_TOKEN, SELLER_*
docker compose up -d --build
curl -sS localhost:8813/api/info      # проверка, что контейнер отвечает
```

**Caddy** — добавить блок из `deploy/chasy.caddy` в `/etc/caddy/Caddyfile`:

```bash
sudo cp /etc/caddy/Caddyfile /etc/caddy/Caddyfile.bak.$(date +%F)
sudo sh -c 'cat ~/Chasy/deploy/chasy.caddy >> /etc/caddy/Caddyfile'
sudo caddy validate --config /etc/caddy/Caddyfile
sudo systemctl reload caddy
```

**Cloudflare** — в DNS зоны `profitsenser.com`:
- запись `A` (или `CNAME`) `chasy` → IP сервера, **Proxied (оранжевое облако)**;
- SSL/TLS mode: **Full (strict)** — Caddy получит настоящий Let's Encrypt сертификат.
- Cloudflare шлёт `CF-Connecting-IP` → приложение использует его для rate-limit.

### Что заполнить в `.env`

| Переменная | Что это |
|---|---|
| `BASE_URL` | `https://chasy.profitsenser.com` — попадает в ссылки из писем |
| `APP_PORT` | локальный порт (по умолчанию `8813`), тот же в `deploy/chasy.caddy` |
| `SECRET_KEY` | `openssl rand -hex 32` |
| `POSTGRES_PASSWORD` | `openssl rand -hex 24` |
| `SMTP_*` | почтовый сервер для писем. Пусто → ссылка в `docker compose logs -f app` |
| `ADMIN_USER` / `ADMIN_TOKEN` | вход в `/admin` (см. раздел про монетизацию) |
| `SELLER_*` | реквизиты для счёта (см. раздел про счета) |

## Локальный тест без домена и почты

```bash
cp .env.example .env
# в .env:  BASE_URL=http://localhost:8813   DEV_ECHO_MAGIC_LINK=true
docker compose up --build
# открыть http://localhost:8813 , ссылку для входа взять из логов app
```

## Монетизация — коды доступа (вариант A)

По умолчанию выключено (`LICENSE_REQUIRED=false`) — приложение бесплатно для всех.

Чтобы включить продажу по кодам, в `.env`:

```
LICENSE_REQUIRED=true
TRIAL_DAYS=14                       # 0 = без пробного периода
ADMIN_TOKEN=<openssl rand -hex 24>  # пусто = админка выключена
```

Как это работает:
- новый пользователь после входа по ссылке вводит **код доступа**;
- у кода есть срок (`действует до`) и опц. лимит мест;
- когда срок истёк — приложение переходит в режим **только чтение**: просмотр и
  экспорт Excel работают, добавление/изменение/удаление/импорт заблокированы,
  данные не теряются;
- продление = поменять дату у кода в админке.

**Админка:** `https://<домен>/admin` — вводишь `ADMIN_TOKEN`, создаёшь коды
(компания, свой текст кода или автогенерация, срок, места), продлеваешь и
отключаешь их, смотришь список пользователей и можешь отвязать код от аккаунта.

**Бесплатно без кода:**
- `FREE_EMAIL_DOMAINS=ges-rent.sk` — все с почтой на этом домене работают
  сразу, без ввода кода и без баннера.
- `PROMO_CODES=MayDay2027` — этот код всегда действует (создаётся при старте
  как бессрочный, без лимита мест); регистр не важен. Раздаёшь его — у кого
  он введён, тем бесплатно навсегда.

Продажа — вручную: выставляешь счёт / получаешь перевод → создаёшь код в
админке → отправляешь его клиенту. Цену удобнее делать фиксированной за
компанию в месяц.

**Условия и согласие:**
- текст лежит в `frontend/terms.html`, открывается по `/terms`;
- при активации кода пользователь ставит галочку «принимаю условия» —
  дата и версия (`TOS_VERSION`) сохраняются в `users.tos_accepted_at` /
  `users.tos_version`. Меняешь текст `terms.html` → поднимаешь `TOS_VERSION`
  в `.env`.
- Цена показывается в окне «О программе» (из `INVOICE_PRICE`/`INVOICE_CURRENCY`).
- Пользователи с почтой из `FREE_EMAIL_DOMAINS` (напр. `ges-rent.sk`)
  заходят бесплатно автоматически, без кода и без окна согласия.

**Счёт (проформа):**
- Заполни в `.env` `SELLER_NAME` и `SELLER_IBAN` (+ адрес, `SELLER_REG_ID`,
  `SELLER_BANK`, `SELLER_EMAIL`, `INVOICE_NOTE`) — появится ссылка
  «Сформировать счёт» в окне «О программе».
- Клиент вводит свои реквизиты (компания, IČO, DIČ, адрес, число месяцев)
  на `/invoice` → получает **зálohovú faktúru** (проформу) с суммой,
  IBAN, переменным символом и пометкой про Wise → печатает в PDF, платит.
- Номера — сквозные (`PF{год}{NNNN}`), переменный символ = цифры номера.
- Все выписанные счета видны в `/admin` (раздел «Счета»).
- Твои платёжные реквизиты только в `.env` (gitignore) и в самом счёте,
  который открывает залогиненный клиент; в репозитории их нет.
- Это **проформа/счёт на оплату**, не налоговый документ. После оплаты
  при необходимости выставляешь клиенту обычную фактуру.

## Защита от ботов

Без капчи — для инструмента на десяток компаний хватает:
- **Rate-limit** на `POST /api/auth/request` (запрос ссылки для входа):
  не чаще 1 письма в `AUTH_MIN_INTERVAL_SEC` на адрес, ≤ `AUTH_MAX_LIVE_TOKENS`
  неиспользованных ссылок на адрес, ≤ `AUTH_MAX_PER_MIN_PER_IP` в минуту и
  ≤ `AUTH_MAX_PER_HOUR_PER_IP` в час на IP. Превышение → `429`.
- **Honeypot**: скрытое поле `website` в форме входа; если бот его заполнил —
  ответ «успех», но письмо не отправляется.
- Реальный IP берётся из `X-Real-IP`, который ставит Caddy (`{remote_host}`,
  перезаписывается — подделать нельзя).
- Мягкий лимит на `POST /api/license/redeem` (20 попыток / 10 мин на IP).

Капчу (Cloudflare Turnstile) стоит добавлять только при реальном абьюзе.

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
