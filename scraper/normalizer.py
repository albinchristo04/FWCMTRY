import re
from datetime import datetime, timezone
from urllib.parse import urlparse


def normalize_match(raw: dict, source_url: str) -> dict:
    match = {}

    title = (raw.get("title") or "").strip()
    if title:
        match["title"] = title
        # icdb.tv uses "Team v Team"; also handle "Team vs Team" for other sources
        parts = re.split(r"\s+vs?\.?\s+", title, flags=re.IGNORECASE)
        if len(parts) == 2:
            match["teams"] = [p.strip() for p in parts]

    # Handle combined datetime field from icdb.tv ("28/06/2026 05:00")
    datetime_str = (raw.get("datetime") or "").strip()
    if datetime_str:
        dt_parts = datetime_str.split(" ", 1)
        match["date"] = dt_parts[0]
        if len(dt_parts) == 2:
            match["time"] = dt_parts[1]
    else:
        for field in ("date", "time"):
            val = (raw.get(field) or "").strip()
            if val:
                match[field] = val

    for field in ("tournament", "venue"):
        val = (raw.get(field) or "").strip()
        if val:
            match[field] = val

    for field in ("channels", "commentators"):
        val = raw.get(field)
        if isinstance(val, str):
            items = [s.strip() for s in val.split(",") if s.strip()]
        elif isinstance(val, list):
            items = [s.strip() for s in val if (s or "").strip()]
        else:
            items = []
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
