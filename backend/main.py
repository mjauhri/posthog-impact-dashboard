import traceback
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

from github_client import GitHubAPIError
from ingestion import RepoImpactService

app = FastAPI(title="PostHog Impact Dashboard API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

service = RepoImpactService(owner="PostHog", repo="posthog")


@app.get("/api/summary")
def summary(days: int = Query(default=90, ge=30, le=365), refresh: bool = False):
    try:
        return service.compute_dashboard(days=days, refresh=refresh)
    except GitHubAPIError as exc:
        return {"error": str(exc)}
    except Exception as exc:
        traceback.print_exc()
        return {"error": f"Unexpected server error: {type(exc).__name__}: {exc}"}


@app.get("/api/engineers")
def engineers(
    days: int = Query(default=90, ge=30, le=365),
    sort: str = Query(default="score"),
    refresh: bool = False,
):
    try:
        payload = service.compute_dashboard(days=days, refresh=refresh)
        rows = payload["engineers"]
        valid = {"score", "ownership", "breadth", "leverage", "execution"}
        key = sort if sort in valid else "score"
        return sorted(rows, key=lambda item: item[key], reverse=True)
    except GitHubAPIError as exc:
        return {"error": str(exc)}
    except Exception as exc:
        traceback.print_exc()
        return {"error": f"Unexpected server error: {type(exc).__name__}: {exc}"}


@app.get("/api/rate-limit")
def rate_limit():
    try:
        return service.client.get_rate_limit()
    except GitHubAPIError as exc:
        return {"error": str(exc)}
    except Exception as exc:
        traceback.print_exc()
        return {"error": f"Unexpected server error: {type(exc).__name__}: {exc}"}
