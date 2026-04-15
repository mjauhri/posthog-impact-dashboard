# Deploying the PostHog Impact Dashboard

This project is set up for:

- **Frontend:** Vercel
- **Backend:** Render

## 1) Deploy the backend to Render

Push this repo to GitHub, then in Render either:

- create a new **Blueprint** using the `render.yaml` in the repo root, or
- create a new **Web Service** manually

### Using the included blueprint

Render will read:

- `rootDir: backend`
- `buildCommand: pip install -r requirements.txt`
- `startCommand: uvicorn main:app --host 0.0.0.0 --port $PORT`

### Required environment variable

Set this in Render:

```bash
GITHUB_TOKEN=your_github_token_here
```

This is strongly recommended to avoid GitHub API rate limits.

After deploy, copy the backend URL, for example:

```bash
https://posthog-impact-api.onrender.com
```

## 2) Deploy the frontend to Vercel

Import the GitHub repo into Vercel.

Use these settings:

- **Framework preset:** Vite
- **Root directory:** `frontend`

### Required environment variable

In the Vercel project settings, add:

```bash
VITE_API_BASE=https://posthog-impact-api.onrender.com
```

Then redeploy.

## 3) Local development

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export GITHUB_TOKEN=your_github_token_here
uvicorn main:app --reload
```

### Frontend

```bash
cd frontend
cp .env.example .env.local
npm install
npm run dev
```

## 4) Important frontend setting already included

The frontend now uses:

```js
const API_BASE = import.meta.env.VITE_API_BASE || "http://127.0.0.1:8000";
```

So it works locally and in production.

## 5) Share it

Once both deploys succeed, share the Vercel URL. The React app will call the Render backend using the `VITE_API_BASE` you configured.
