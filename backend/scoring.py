from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Tuple


KEYWORD_WEIGHTS = {
    "feat": 2.4,
    "feature": 2.4,
    "refactor": 2.1,
    "perf": 2.2,
    "optimize": 2.0,
    "fix": 1.7,
    "reliability": 2.0,
    "validation": 2.0,
    "migrate": 1.8,
    "infra": 2.0,
    "oauth": 1.8,
    "security": 2.1,
    "cache": 1.7,
    "sync": 1.8,
    "retry": 1.7,
    "test": 1.2,
    "docs": 0.6,
    "chore": 0.7,
}

AREA_RULES: List[Tuple[str, str]] = [
    ("frontend/", "frontend"),
    ("products/", "product"),
    ("posthog/", "backend"),
    ("ee/", "enterprise"),
    ("plugin-server/", "backend"),
    ("rust/", "systems"),
    ("terraform/", "infra"),
    ("docker/", "infra"),
    ("common/", "platform"),
    ("cli/", "platform"),
    ("services/", "platform"),
    ("nodejs/", "platform"),
    ("packages/", "shared-libraries"),
    (".github/", "tooling"),
    ("playwright/", "quality"),
    ("docs/", "docs"),
    ("staticfiles/", "frontend"),
]


def normalize_title(title: str) -> str:
    return re.sub(r"[^a-z0-9\s:/_-]+", " ", title.lower()).strip()


def keyword_score(title: str) -> float:
    words = normalize_title(title)
    score = 0.0
    for token, weight in KEYWORD_WEIGHTS.items():
        if token in words:
            score += weight
    return score


def classify_area(filename: str) -> str:
    path = filename.lower()
    for prefix, area in AREA_RULES:
        if path.startswith(prefix):
            return area
    return "other"


def is_test_file(filename: str) -> bool:
    path = filename.lower()
    return any(part in path for part in ["/test", "/tests", "__tests__", ".spec.", ".test.", "playwright/"])


def is_infra_file(filename: str) -> bool:
    path = filename.lower()
    return path.startswith(("terraform/", "docker/", ".github/"))


def shared_primitive_signal(filename: str) -> bool:
    path = filename.lower()
    return any(
        token in path
        for token in [
            "common/",
            "packages/",
            "components/",
            "lib/",
            "utils/",
            "schema",
            "types",
            "api/",
        ]
    )


@dataclass
class PREntry:
    number: int
    title: str
    url: str
    merged_at: str
    author: str
    additions: int
    deletions: int
    changed_files: int
    commits: int
    files: List[str]


def extract_pr_features(pr: PREntry) -> Dict[str, Any]:
    touched_areas = [classify_area(name) for name in pr.files]
    area_counts = Counter(touched_areas)

    cross_cutting_bonus = 1.0 + min(len(area_counts), 5) * 0.25
    size_signal = min(pr.changed_files, 40) / 10.0
    commit_signal = min(pr.commits, 12) / 4.0
    keyword_signal = keyword_score(pr.title)

    reliability_signal = 0.0
    if any(token in normalize_title(pr.title) for token in ["fix", "retry", "validation", "error", "oauth", "perf", "race", "cache"]):
        reliability_signal += 1.8
    if any(is_test_file(name) for name in pr.files):
        reliability_signal += 0.7
    if any(is_infra_file(name) for name in pr.files):
        reliability_signal += 0.8

    leverage_signal = 0.0
    if any(shared_primitive_signal(name) for name in pr.files):
        leverage_signal += 1.8
    if len(area_counts) >= 2:
        leverage_signal += 0.8
    if any(area in area_counts for area in ["infra", "platform", "systems", "shared-libraries"]):
        leverage_signal += 1.0

    ownership_signal = 1.0 + (area_counts.most_common(1)[0][1] / max(len(pr.files), 1)) * 1.5
    product_signal = 1.0 + min(len([a for a in area_counts if a not in {"docs", "tooling"}]), 4) * 0.5

    pr_impact = (
        4.0
        + keyword_signal
        + cross_cutting_bonus
        + size_signal
        + commit_signal
        + reliability_signal
        + leverage_signal
        + ownership_signal
        + product_signal
    )

    return {
        "pr_impact": round(pr_impact, 2),
        "areas": area_counts,
        "reliability_signal": reliability_signal,
        "leverage_signal": leverage_signal,
        "ownership_signal": ownership_signal,
        "product_signal": product_signal,
    }


def summarize_engineers(prs: Iterable[PREntry], top_n: int = 5) -> List[Dict[str, Any]]:
    per_author: Dict[str, Dict[str, Any]] = defaultdict(
        lambda: {
            "name": "",
            "prs": [],
            "area_counts": Counter(),
            "impact_total": 0.0,
            "reliability_total": 0.0,
            "leverage_total": 0.0,
            "ownership_total": 0.0,
            "product_total": 0.0,
        }
    )

    for pr in prs:
        features = extract_pr_features(pr)
        bucket = per_author[pr.author]
        bucket["name"] = pr.author
        bucket["prs"].append({"pr": pr, "features": features})
        bucket["impact_total"] += features["pr_impact"]
        bucket["reliability_total"] += features["reliability_signal"]
        bucket["leverage_total"] += features["leverage_signal"]
        bucket["ownership_total"] += features["ownership_signal"]
        bucket["product_total"] += features["product_signal"]
        bucket["area_counts"].update(features["areas"])

    if not per_author:
        return []

    max_impact = max(v["impact_total"] for v in per_author.values()) or 1.0
    max_reliability = max(v["reliability_total"] for v in per_author.values()) or 1.0
    max_leverage = max(v["leverage_total"] for v in per_author.values()) or 1.0
    max_ownership = max(v["ownership_total"] for v in per_author.values()) or 1.0
    max_product = max(v["product_total"] for v in per_author.values()) or 1.0

    scored = []
    for author, bucket in per_author.items():
        dominant_areas = [area for area, _ in bucket["area_counts"].most_common(3)]
        ownership = round(100 * bucket["ownership_total"] / max_ownership)
        breadth = round(100 * bucket["product_total"] / max_product)
        leverage = round(100 * bucket["leverage_total"] / max_leverage)
        execution = round(100 * bucket["reliability_total"] / max_reliability)

        blended = (
            0.34 * (bucket["impact_total"] / max_impact)
            + 0.24 * (bucket["ownership_total"] / max_ownership)
            + 0.18 * (bucket["product_total"] / max_product)
            + 0.16 * (bucket["leverage_total"] / max_leverage)
            + 0.08 * (bucket["reliability_total"] / max_reliability)
        )
        score = round(blended * 100)

        top_prs = sorted(bucket["prs"], key=lambda item: item["features"]["pr_impact"], reverse=True)[:6]
        area = " / ".join(dominant_areas) if dominant_areas else "mixed"

        strengths = [
            f"Strongest concentration in {dominant_areas[0] if dominant_areas else 'mixed work'}",
            f"{len(bucket['prs'])} merged PRs in the selected window",
            "Repeated work pattern suggests ownership rather than one-off drive-by changes",
        ]
        risks = [
            "Public repo signals miss review quality and internal coordination load",
            "Outcome data such as adoption or incident reduction is not included",
        ]

        why = (
            f"Ranks highly because they combined repeated ownership in {area} with "
            f"{len(bucket['prs'])} merged PRs whose titles and changed files suggest "
            f"meaningful delivery, leverage, and reliability work."
        )

        evidence = [
            {
                "pr": f"{item['pr'].title} (#{item['pr'].number})",
                "meta": f"Merged {item['pr'].merged_at[:10]} · impact {item['features']['pr_impact']}",
            }
            for item in top_prs
        ]

        scored.append(
            {
                "name": author,
                "area": area,
                "score": score,
                "ownership": ownership,
                "breadth": breadth,
                "leverage": leverage,
                "execution": execution,
                "why": why,
                "strengths": strengths,
                "risks": risks,
                "evidence": evidence,
                "chips": dominant_areas[:5] or ["mixed"],
                "raw": {
                    "impact_total": round(bucket["impact_total"], 2),
                    "pr_count": len(bucket["prs"]),
                    "area_counts": bucket["area_counts"],
                },
            }
        )

    return sorted(scored, key=lambda item: (item["score"], item["raw"]["impact_total"]), reverse=True)[:top_n]
