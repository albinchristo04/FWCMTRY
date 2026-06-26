import re
from datetime import datetime, timezone
from urllib.parse import urlparse


def normalize_match(raw: dict, source_url: str) -> dict:
    match = {}

    title = (raw.get("title") or "").strip()
    if title:
        match["title"] = title
        parts = re.split(r"\s+vs\.?\s+", title, flags=re.IGNORECASE)
        if len(parts) == 2:
            match["teams"] = [p.strip() for p in parts]

    for field in ("date", "time", "tournament", "venue"):
        val = (raw.get(field) or "").strip()
        if val:
            match[field] = val

    for field in ("channels", "commentators"):
        items = [s.strip() for s in (raw.get(field) or []) if (s or "").strip()]
        if items:
            match[field] = items

    url = (raw.get("match_url") or "").strip()
    if url:
        if url.startswith("/"):
            parsed = urlparse(source_url)
            url = f"{parsed.scheme}://{parsed.netloc}{url}"
        match["match_url"] = url

    return match


def build_output(matches: list[dict], source_url: str) -> dict:
    return {
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "source": source_url,
        "total_matches": len(matches),
        "matches": matches,
    }
