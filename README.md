# PostHog Impact Dashboard — real GitHub ingestion

This version uses the live GitHub API for `PostHog/posthog` and scores engineers automatically.

## What the backend does

1. Pulls merged PRs from the last 90+ days
2. Fetches changed files for each PR
3. Computes automatic signals for:
   - ownership
   - breadth
   - leverage / complexity
   - execution / reliability
4. Ranks the top 5 engineers
5. Caches the result to `backend/.cache.json`

## Backend setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export GITHUB_TOKEN=your_token_here   # recommended, optional for public repos
uvicorn main:app --reload
```

Backend URL:
- `http://127.0.0.1:8000/api/summary`
- `http://127.0.0.1:8000/api/engineers`
- `http://127.0.0.1:8000/api/rate-limit`

Examples:
```bash
curl "http://127.0.0.1:8000/api/summary?days=90&refresh=true"
curl "http://127.0.0.1:8000/api/engineers?days=90&sort=leverage"
```

## Frontend setup

```bash
cd frontend
npm install
npm run dev
```

Frontend URL:
- `http://127.0.0.1:5173`

## Notes on the scoring model

This intentionally avoids using raw lines of code as the main signal.
Instead it looks for:
- repeated work in the same product or platform surface
- cross-cutting PRs
- shared primitives and infra work
- reliability-oriented fixes and tests
- the shape of the changed files, not just the count of PRs

## Practical caveats

- Public GitHub data cannot measure internal influence, reviews, or product outcomes.
- For large windows, unauthenticated requests can hit rate limits. A `GITHUB_TOKEN` is recommended.
- The heuristic model is easy to tune in `backend/scoring.py`.


## Deployment

See `DEPLOY.md` for Vercel + Render deployment instructions and included config files.
