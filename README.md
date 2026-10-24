# Stock Option Analyzer

AdvComPro-Mini-Project-2026 | Marlon and Friends | Submission deadline: 31 October 2026

An educational stock-analysis web app built with Next.js 14 / React 18, FastAPI and PostgreSQL 16. It combines Finnhub market context, Anthropic-generated explanations, local probability estimates, watchlist scanning, history, glossary and manually approved Pro membership.

## Run with Docker Desktop

1. Install Docker Desktop and start its Linux container engine.
2. Copy `.env.example` to `.env` in this directory.
3. Set fresh database, JWT and admin credentials; provide your own Finnhub and Anthropic keys.
4. Run `docker compose up -d --build`.
5. Open http://localhost:3000. API documentation: http://localhost:8000/docs; service check: http://localhost:8000/health.

On Windows, after the first build, `Start-Stock-Analyzer.bat` starts the stack and opens the site (and DBeaver if installed).

## Features

- Register/login with bcrypt password hashes and JWT bearer tokens.
- Stock analysis with price/news context, CALL/PUT explanations, strategy, scenarios and saved history.
- Option levels and a browser strike probability calculator.
- Nine watchlists, including Pro-only categories, with heuristic scoring.
- English glossary, membership requests, manual 30-day approvals and timed membership promotions.

## Structure

- `frontend/`: Next.js app routes, reusable result components and Axios client.
- `backend/`: FastAPI routes, authentication, ORM models, providers, glossary, scanner and probability code.
- `docker-compose.yml`: local services bound to loopback.
- `docker-compose.server.yml`: optional server deployment with exposed frontend; deployment not verified here.
- `tools/verify_features.py`: existing integration checks with mocked scanner input and rollback of test database writes.
- `docs/Stock_Option_Analyzer_Design_Document.pdf`: system design, API, entity model, limitations and acceptance plan.
- `docs/verification.json`: checks performed for this submission bundle.

The original legacy Express/vanilla-JS folders are not part of this Docker build and are deliberately excluded. No account database, real `.env`, installed dependencies or private provider keys are included.

## Database and inspection

The API creates tables at startup. PostgreSQL data lives in the `postgres_data` Docker volume. In DBeaver use host `localhost`, port `5432`, database `stock_analyzer`, username `postgres`, and your configured `POSTGRES_PASSWORD`. Expand Schemas > public > Tables.

## Verification

Offline Python syntax and probability checks passed during document generation. Docker and both localhost services were unavailable on 24 October 2026; fresh end-to-end/provider tests are not claimed. Once running, execute the existing integration checks from PowerShell:

```powershell
Get-Content tools/verify_features.py -Raw | docker compose exec -T backend python -
```

Use a development/test database for verification. Consult the design PDF for the manual acceptance checklist and the known user/date uniqueness gap.

## Important implementation boundaries

No broker orders or automated bank payments are executed. Subscription approval is manual. Scanner option costs and displayed payouts are illustrative, not live option-chain prices. Probability calculations describe terminal prices under assumptions, not strike-touch probability or realized returns. The market selector does not implement an independent Thai-market adapter. The current admin mechanism, CORS policy, token storage and quota concurrency need production hardening; see the design PDF.

## Submission access

Repository: https://github.com/Panupon777/stock-option-analyzer (Public). The assessor can view and clone the source without an invitation. Never upload your real `.env`, personal account data or database backups.
