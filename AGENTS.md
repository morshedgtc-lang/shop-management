# AGENTS.md — Shop Management

## Quick Start

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
# Open http://localhost:8000
# Login: admin@shop.com / admin123
```

## Stack

- **Backend:** FastAPI + SQLAlchemy + PostgreSQL (Railway) or SQLite (local dev)
- **Auth:** JWT via python-jose + bcrypt (NOT passlib — see gotchas)
- **Frontend:** Single-page vanilla HTML/CSS/JS in `static/index.html`
- **Deploy:** Railway (Procfile runs uvicorn)

## Architecture

```
app/
  main.py          — FastAPI app, CORS, startup (init_db), /api/dashboard, /health
  config.py        — env vars via python-dotenv
  database.py      — engine, SessionLocal, Base, init_db() seeds admin + categories + settings
  models/          — 11 SQLAlchemy models (users, customers, repairs, services, parts, etc.)
  schemas/         — Pydantic request/response models
  routes/          — 11 routers, all prefixed /api/<resource>
  utils/auth.py    — JWT helpers, password hashing, role dependencies
static/
  index.html       — complete SPA (login, dashboard, repairs, customers, inventory, etc.)
```

## Gotchas — Read Before Changing Code

### bcrypt (NOT passlib)
`passlib` is incompatible with bcrypt>=4.x on Python 3.13+. Use `bcrypt` directly:
```python
import bcrypt
hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
ok = bcrypt.checkpw(plain.encode(), hashed.encode())
```

### JWT `sub` must be a string
`python-jose` raises `Subject must be a string` if `sub` is an integer:
```python
create_access_token(data={"sub": str(user.id), "role": user.role})
# Decode: user_id = int(payload["sub"])
```

### Route trailing slashes
`redirect_slashes=False` is set on the FastAPI app. All routes use `@router.get("")` (not `@router.get("/")`). If you add new root routes, use `""` to match the frontend calls.

### DATABASE_URL on Railway
Railway auto-injects `DATABASE_URL` from its PostgreSQL plugin. Do NOT put a placeholder DATABASE_URL in `.env.example` — Railway scans source code for variable suggestions and will inject the wrong value. The `database.py` auto-appends `?sslmode=require` for PostgreSQL.

### Frontend API calls
The SPA uses relative URLs (`/api/customers`, not `http://...`). All API calls go through the `api()` helper in `static/index.html` which handles JWT headers and 401 redirects.

## Running Locally

```bash
# Local dev uses SQLite automatically (no DATABASE_URL = shop.db)
python -m uvicorn app.main:app --reload --port 8000
```

## Deployment

Railway auto-deploys from `main` branch. Add PostgreSQL database via Railway dashboard (New → Database → PostgreSQL). Set `JWT_SECRET` env var.
