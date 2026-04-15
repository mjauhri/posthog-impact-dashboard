import os
import time
from typing import Any, Dict, Iterable, List, Optional

import requests


class GitHubAPIError(Exception):
    pass


class GitHubClient:
    def __init__(self, token: Optional[str] = None, api_version: str = "2022-11-28") -> None:
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Accept": "application/vnd.github+json",
                "User-Agent": "posthog-impact-dashboard",
                "X-GitHub-Api-Version": api_version,
            }
        )
        token = token or os.getenv("GITHUB_TOKEN")
        if token:
            self.session.headers["Authorization"] = f"Bearer {token}"

    def _handle_response(self, response: requests.Response) -> Any:
        if response.status_code == 403 and response.headers.get("X-RateLimit-Remaining") == "0":
            reset = response.headers.get("X-RateLimit-Reset")
            if reset:
                sleep_for = max(0, int(reset) - int(time.time())) + 1
                raise GitHubAPIError(f"GitHub rate limit exceeded. Retry after ~{sleep_for}s or use GITHUB_TOKEN.")
            raise GitHubAPIError("GitHub rate limit exceeded. Use GITHUB_TOKEN.")
        if response.status_code >= 400:
            raise GitHubAPIError(f"GitHub API error {response.status_code}: {response.text[:300]}")
        return response.json()

    def get(self, url: str, params: Optional[Dict[str, Any]] = None) -> Any:
        response = self.session.get(url, params=params, timeout=30)
        return self._handle_response(response)

    def paginate(self, url: str, params: Optional[Dict[str, Any]] = None) -> Iterable[List[Dict[str, Any]]]:
        page = 1
        while True:
            current = dict(params or {})
            current["page"] = page
            current.setdefault("per_page", 100)
            data = self.get(url, current)
            if not data:
                break
            yield data
            if len(data) < current["per_page"]:
                break
            page += 1

    def get_rate_limit(self) -> Dict[str, Any]:
        return self.get("https://api.github.com/rate_limit")
