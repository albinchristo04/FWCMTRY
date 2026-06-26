# icdb.tv Match Scraper — Design Spec

**Date:** 2026-06-26  
**Status:** Approved  
**Source:** https://icdb.tv/

---

## Overview

A Python scraper that extracts match schedules, broadcast channels, and commentator details from icdb.tv every 5 hours via GitHub Actions. Results are committed to the repo as `data/matches.json` and uploaded as a GitHub Actions artifact per run.

---

## File Layout

```
FWCMTRY/
├── scraper/
│   └── scrape.py          # Main crawl4ai scraper
├── data/
│   └── matches.json       # Output — committed every run
├── requirements.txt       # Python dependencies
└── .github/
    └── workflows/
        └── scrape.yml     # Runs every 5 hours
```

---

## Data Model

`data/matches.json` shape:

```json
{
  "scraped_at": "2026-06-26T07:30:00Z",
  "source": "https://icdb.tv/",
  "total_matches": 12,
  "matches": [
    {
      "title": "India vs Australia",
      "date": "2026-06-26",
      "time": "14:00",
      "timezone": "UTC",
      "teams": ["India", "Australia"],
      "tournament": "ICC World Cup 2026",
      "venue": "Lords, London",
      "channels": ["Star Sports 1", "Hotstar"],
      "commentators": ["Ravi Shastri", "Sanjay Manjrekar"],
      "match_url": "https://icdb.tv/match/..."
    }
  ]
}
```

**Rules:**
- `scraped_at` is always ISO 8601 UTC.
- Fields absent from the page for a given match are omitted entirely (not set to `null`).
- `teams` is derived by splitting `title` on " vs " — raw `title` is always preserved.
- All fields are strings or arrays of strings; no nested objects.

---

## Scraper Design (`scraper/scrape.py`)

### Library
[crawl4ai](https://github.com/unclecode/crawl4ai) — open-source, runs headless Chromium via Playwright, no API key required.

### Behavior
- Uses `AsyncWebCrawler` with `BrowserConfig(browser_type="chromium", headless=True)`.
- Waits for match content to render: `CrawlerRunConfig(wait_for="css:.match-card, .fixture, table tr")`.
- Extraction via `JsonCssExtractionStrategy` with a schema mapping CSS selectors to JSON fields.
- If a selector returns nothing, the field is omitted — no crash.
- Writes atomically: builds full dict in memory, single `json.dump` to `data/matches.json`.
- `--dry-run` flag: prints JSON to stdout, skips file write (for local testing).
- Exits with code `1` on unrecoverable error so the Actions run is marked failed.

### CSS Selector Targets
These selectors must be verified against live HTML on the first run and updated if needed:

| Field | Selector |
|---|---|
| Match title | `.match-title`, `.fixture-name`, or `h2`/`h3` inside match card |
| Date / Time | `.match-date`, `.fixture-time`, `time` element |
| Channels | `.channel`, `.broadcaster`, `img[alt]` in broadcast section |
| Commentators | `.commentator`, `.commenter-name`, list items in commentary section |
| Match URL | `a[href]` on the match card |

> **First-run task:** Inspect icdb.tv's rendered HTML (DevTools → Elements) to confirm or update selectors before pushing to CI.

---

## GitHub Actions Workflow (`.github/workflows/scrape.yml`)

### Triggers
- `schedule: cron: '0 */5 * * *'` — fires at 00:00, 05:00, 10:00, 15:00, 20:00 UTC daily.
- `workflow_dispatch` — manual trigger for on-demand runs.

### Permissions
```yaml
permissions:
  contents: write
```

### Steps
1. `actions/checkout@v4` with `persist-credentials: true`
2. `actions/setup-python@v5` — Python 3.12
3. `pip install -r requirements.txt`
4. `crawl4ai-setup` — installs Playwright Chromium (required once per runner)
5. `python scraper/scrape.py` — fails the run on exit code 1
6. **Commit step:**
   ```bash
   git diff --quiet data/matches.json || \
     (git add data/matches.json && \
      git commit -m "chore: update matches [skip ci]" && \
      git push)
   ```
   `[skip ci]` prevents the push from triggering another workflow run.
7. `actions/upload-artifact@v4` — uploads `data/matches.json`, `retention-days: 30`

### Secrets Required
None — crawl4ai runs fully inside the runner with no external API keys.

---

## Error Handling

| Scenario | Behavior |
|---|---|
| Site unreachable / timeout | Script exits 1, run marked failed, no file written |
| Selectors return empty results | Warning logged, empty `matches: []` written, run succeeds |
| Git push conflict | Workflow fails on push step; re-run manually |
| No changes to JSON | Commit step skipped via `git diff --quiet` |

---

## Out of Scope
- Pagination / crawling sub-pages beyond the main listing
- Historical data retention beyond artifact 30-day window
- Notifications or alerting on scrape failures
- LLM-based extraction (CSS selectors chosen for cost-free runs)
