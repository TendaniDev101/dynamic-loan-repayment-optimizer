# dynamic-loan-repayment-optimizer

A small loan planning tool for testing repayment strategies before committing to a long-term debt path.

It combines a React frontend with a FastAPI backend to show:
- base repayment amount
- total paid and interest paid
- savings from extra repayments
- payoff term reduction
- amortization schedule and payment composition

The project also includes a Cloudflare Worker setup so the FastAPI API and built frontend can be served from the same Cloudflare deployment.

## Run locally

```bash
./start_calculator.sh
```

The app starts the backend and frontend dev servers for local development.

## Run with Docker

```bash
docker compose up --build
```

Then open `http://localhost:8000`.

## Run on Cloudflare Workers

Install the required local tools first:
- Node.js 24+
- `uv`

Then install dependencies and start local Worker development:

```bash
cd frontend && npm install && cd ..
uv sync --group dev
uv run pywrangler dev
```

To deploy to Cloudflare:

```bash
uv run pywrangler deploy
```

The Worker configuration lives in `wrangler.jsonc`, the Python Worker entrypoint is `worker.py`, and the frontend is deployed as static assets from `frontend/dist`.

For local backend and Docker workflows, Python runtime dependencies are kept in `requirements.local.txt`.

## Stack

- React + Vite
- FastAPI
- Cloudflare Workers (Python)
- Docker / Docker Compose
