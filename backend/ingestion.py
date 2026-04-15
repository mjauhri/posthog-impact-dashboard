from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List

from github_client import GitHubClient
from scoring import PREntry, summarize_engineers

CACHE_PATH = Path(__file__).resolve().parent / ".cache.json"


class RepoImpactService:
    def __init__(self, owner: str = "PostHog", repo: str = "posthog") -> None:
        self.owner = owner
        self.repo = repo
        self.client = GitHubClient()

    def _pulls_url(self) -> str:
        return f"https://api.github.com/repos/{self.owner}/{self.repo}/pulls"

    def _pull_files_url(self, pull_number: int) -> str:
        return f"https://api.github.com/repos/{self.owner}/{self.repo}/pulls/{pull_number}/files"

    def fetch_recent_merged_prs(self, days: int = 90, max_prs: int = 250) -> List[PREntry]:
        since = datetime.now(timezone.utc) - timedelta(days=days)
        results: List[PREntry] = []

        for page in self.client.paginate(
            self._pulls_url(),
            params={"state": "closed", "sort": "updated", "direction": "desc", "per_page": 100},
        ):
            stop = False
            for pr in page:
                merged_at = pr.get("merged_at")
                if not merged_at:
                    continue
                merged_dt = datetime.fromisoformat(merged_at.replace("Z", "+00:00"))
                if merged_dt < since:
                    stop = True
                    continue

                files = []
                for files_page in self.client.paginate(self._pull_files_url(pr["number"]), params={"per_page": 100}):
                    files.extend(item["filename"] for item in files_page)

                results.append(
                    PREntry(
                        number=pr["number"],
                        title=pr["title"],
                        url=pr["html_url"],
                        merged_at=merged_at,
                        author=(pr.get("user") or {}).get("login", "unknown"),
                        additions=pr.get("additions", 0),
                        deletions=pr.get("deletions", 0),
                        changed_files=pr.get("changed_files", 0),
                        commits=pr.get("commits", 0),
                        files=files,
                    )
                )
                if len(results) >= max_prs:
                    return results
            if stop:
                break

        return results

    def compute_dashboard(self, days: int = 90, top_n: int = 5, refresh: bool = False) -> Dict[str, Any]:
        if CACHE_PATH.exists() and not refresh:
            cached = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
            if cached.get("days") == days and "engineers" in cached:
                return cached

        prs = self.fetch_recent_merged_prs(days=days)
        engineers = summarize_engineers(prs, top_n=top_n)
        payload = {
            "repo": f"{self.owner}/{self.repo}",
            "days": days,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "pr_count": len(prs),
            "engineers": engineers,
        }
        CACHE_PATH.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
        return payload
