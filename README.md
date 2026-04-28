# InventAI

InventAI is an inventory intelligence app built for Indian retail operations. It helps a store team move from raw sales exports to something actionable: cleaner data, better demand forecasts, reorder suggestions, mandi price context, and an assistant that can explain what is going on.

This is a full-stack project with a FastAPI backend and a React/Vite frontend. The current deployment setup is intentionally straightforward:

- Frontend on Vercel
- Backend on Render
- PostgreSQL on Supabase
- Background jobs handled inside FastAPI

## What the app covers

- CSV upload with preview, column mapping help, and anomaly detection
- Demand forecasting by store and SKU
- Reorder recommendations based on forecast and stock position
- Live mandi price lookups from OGD India when an API key is configured
- Gemini-powered assistant for inventory and forecast questions
- User-level data isolation with Google sign-in

## Tech stack

### Backend

- FastAPI
- SQLAlchemy
- Alembic
- PostgreSQL
- Google OAuth
- Gemini API

### Frontend

- React 19
- Vite
- React Router
- Tailwind CSS
- Chart.js

## How it is put together

Forecast requests are queued through FastAPI `BackgroundTasks` and tracked in the database. The frontend polls by `task_id`, so the forecasting flow behaves like an async job system without needing Redis or a separate worker process.

Database migrations are applied on backend startup through Alembic before the API begins serving traffic.

## Project structure

```text
backend/
  alembic/
  app/
    api/
    config/
    core/
    models/
    schemas/
    services/
  tests/

frontend/
  public/
  src/
    components/
    context/
    pages/
    services/
    styles/
```

## Running locally

### Docker Compose

```bash
docker compose up --build
```

That starts:

- Frontend at `http://localhost:5173`
- Backend at `http://localhost:8002`
- API docs at `http://localhost:8002/docs`
- PostgreSQL at `localhost:5432`

### Run services directly

Backend:

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8002
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

## Environment variables

### Backend

Required in production:

- `APP_ENV`
- `DATABASE_URL`
- `JWT_SECRET_KEY`
- `ENCRYPTION_KEY`
- `ADMIN_INIT_TOKEN`
- `FRONTEND_URL`
- `ALLOWED_ORIGINS`

Required for Google sign-in:

- `GOOGLE_CLIENT_ID`

Optional integrations:

- `GEMINI_API_KEY`
- `GEMINI_MODEL`
- `OGD_INDIA_API_KEY`

### Frontend

- `VITE_API_URL`

Example:

```env
VITE_API_URL=https://your-render-app.onrender.com
```

## Deployment

### Render

The backend includes [backend/render.yaml](backend/render.yaml) with:

- root directory set to `backend`
- build command `pip install -r requirements.txt`
- start command `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

### Vercel

The frontend includes:

- [frontend/.env.production](frontend/.env.production)
- [frontend/vercel.json](frontend/vercel.json)

`vercel.json` rewrites all routes to `index.html` so client-side routing survives direct navigation and refresh.

## Testing

Run backend tests from `backend/`:

```bash
pytest
```

The current test suite covers forecasting behavior, CSV validation, startup database prep, and the task-status flow used by the frontend.

## Workflow the product is built around

This repo is meant to support a practical store workflow, not just show charts:

1. Upload sales data
2. Check the preview and anomalies
3. Run a forecast
4. Review reorder recommendations
5. Compare with mandi prices
6. Ask the assistant for a quick interpretation

If Gemini or live mandi pricing is unavailable, the core inventory workflow still works. That is a deliberate choice.
