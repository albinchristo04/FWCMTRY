# icdb.tv Match Scraper Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python scraper that extracts match schedules, channels, and commentators from icdb.tv every 5 hours via GitHub Actions, committing results to `data/matches.json` and uploading them as a GitHub Actions artifact.

**Architecture:** crawl4ai renders icdb.tv with headless Chromium, extracts structured data via `JsonCssExtractionStrategy` using CSS selectors, and passes raw output to a pure normalizer that produces clean match dicts. The CLI entrypoint orchestrates crawl → normalize → write and is invoked by a GitHub Actions workflow on a 5-hour cron.

**Tech Stack:** Python 3.12, crawl4ai ≥ 0.4.0, Playwright (Chromium), pytest, pytest-asyncio, GitHub Actions

## Global Constraints

- Python 3.12 only
- crawl4ai ≥ 0.4.0
- Fields absent from a match are omitted entirely (never set to null)
- `scraped_at` is always ISO 8601 UTC with `+00:00` offset
- Script exits with code 1 on unrecoverable crawl failure
- All auto-commits include `[skip ci]` to prevent workflow loops
- No external API keys required

---

## File Map

| File | Responsibility |
|---|---|
| `requirements.txt` | Python dependencies |
| `pytest.ini` | pytest async mode config |
| `scraper/__init__.py` | Package marker |
| `scraper/normalizer.py` | Pure functions: raw dict → clean match dict |
| `scraper/scrape.py` | crawl4ai crawler, CSS schema, CLI entrypoint |
| `tests/__init__.py` | Package marker |
| `tests/test_normalizer.py` | Unit tests for normalizer (no mocks needed) |
| `tests/test_scrape.py` | Tests for scraper and CLI (mock AsyncWebCrawler) |
| `data/matches.json` | Output file tracked in git |
| `.github/workflows/scrape.yml` | 5-hour cron, commit step, artifact upload |

---

### Task 1: Project scaffolding

**Files:**
- Create: `requirements.txt`
- Create: `pytest.ini`
- Create: `scraper/__init__.py`
- Create: `tests/__init__.py`
- Create: `data/matches.json`

**Interfaces:**
- Produces: Python package `scraper`, test runner configured for asyncio auto mode

- [ ] **Step 1: Create `requirements.txt`**

```
crawl4ai>=0.4.0
pytest>=8.0
pytest-asyncio>=0.23
```

- [ ] **Step 2: Create `pytest.ini`**

```ini
[pytest]
asyncio_mode = auto
```

- [ ] **Step 3: Create `scraper/__init__.py`** (empty file)

- [ ] **Step 4: Create `tests/__init__.py`** (empty file)

- [ ] **Step 5: Create `data/matches.json`** with empty structure

```json
{
  "scraped_at": "",
  "source": "https://icdb.tv/",
  "total_matches": 0,
  "matches": []
}
```

- [ ] **Step 6: Install dependencies**

```bash
pip install -r requirements.txt
crawl4ai-setup
```

Expected: crawl4ai and pytest installed; Playwright Chromium downloaded.

- [ ] **Step 7: Verify the test runner works**

```bash
pytest --collect-only
```

Expected: `no tests ran` with no errors.

- [ ] **Step 8: Commit**

```bash
git add requirements.txt pytest.ini scraper/__init__.py tests/__init__.py data/matches.json
git commit -m "feat: scaffold scraper project structure"
```

---

### Task 2: Data normalizer

**Files:**
- Create: `tests/test_normalizer.py`
- Create: `scraper/normalizer.py`

**Interfaces:**
- Consumes: raw dict from crawl4ai (keys: `title`, `date`, `time`, `tournament`, `venue`, `channels`, `commentators`, `match_url`), `source_url: str`
- Produces:
  - `normalize_match(raw: dict, source_url: str) -> dict`
  - `build_output(matches: list[dict], source_url: str) -> dict`

- [ ] **Step 1: Write failing tests in `tests/test_normalizer.py`**

```python
from scraper.normalizer import normalize_match, build_output


def test_splits_teams_from_vs_title():
    result = normalize_match({"title": "India vs Australia"}, "https://icdb.tv/")
    assert result["teams"] == ["India", "Australia"]


def test_splits_teams_case_insensitive():
    result = normalize_match({"title": "India VS Australia"}, "https://icdb.tv/")
    assert result["teams"] == ["India", "Australia"]


def test_no_teams_when_no_vs():
    result = normalize_match({"title": "Cricket Finals"}, "https://icdb.tv/")
    assert result["title"] == "Cricket Finals"
    assert "teams" not in result


def test_omits_empty_string_fields():
    result = normalize_match({"title": "A vs B", "venue": "", "tournament": " "}, "https://icdb.tv/")
    assert "venue" not in result
    assert "tournament" not in result


def test_omits_empty_list_fields():
    result = normalize_match({"channels": [], "commentators": []}, "https://icdb.tv/")
    assert "channels" not in result
    assert "commentators" not in result


def test_omits_none_fields():
    result = normalize_match({"title": "A vs B", "channels": None}, "https://icdb.tv/")
    assert "channels" not in result


def test_strips_whitespace_from_channels():
    result = normalize_match({"channels": [" Star Sports 1 ", " Hotstar"]}, "https://icdb.tv/")
    assert result["channels"] == ["Star Sports 1", "Hotstar"]


def test_filters_blank_commentators():
    result = normalize_match({"commentators": ["Ravi Shastri", "", "  "]}, "https://icdb.tv/")
    assert result["commentators"] == ["Ravi Shastri"]


def test_resolves_relative_match_url():
    result = normalize_match({"match_url": "/match/123"}, "https://icdb.tv/")
    assert result["match_url"] == "https://icdb.tv/match/123"


def test_keeps_absolute_match_url():
    result = normalize_match({"match_url": "https://icdb.tv/match/456"}, "https://icdb.tv/")
    assert result["match_url"] == "https://icdb.tv/match/456"


def test_build_output_structure():
    matches = [{"title": "A vs B", "teams": ["A", "B"]}]
    output = build_output(matches, "https://icdb.tv/")
    assert output["source"] == "https://icdb.tv/"
    assert output["total_matches"] == 1
    assert output["matches"] == matches
    assert "+00:00" in output["scraped_at"]


def test_build_output_empty_matches():
    output = build_output([], "https://icdb.tv/")
    assert output["total_matches"] == 0
    assert output["matches"] == []
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_normalizer.py -v
```

Expected: `ModuleNotFoundError: No module named 'scraper.normalizer'`

- [ ] **Step 3: Implement `scraper/normalizer.py`**

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_normalizer.py -v
```

Expected: all 12 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/test_normalizer.py scraper/normalizer.py
git commit -m "feat: add match data normalizer with tests"
```

---

### Task 3: Scraper core and CLI

**Files:**
- Create: `tests/test_scrape.py`
- Create: `scraper/scrape.py`

**Interfaces:**
- Consumes: `normalize_match(raw: dict, source_url: str) -> dict` and `build_output(matches: list[dict], source_url: str) -> dict` from `scraper.normalizer`
- Produces:
  - `scrape() -> list[dict]` — async, returns normalized match list, exits 1 on crawl failure
  - `main() -> None` — CLI entrypoint, `--dry-run` prints JSON to stdout instead of writing file

- [ ] **Step 1: Write failing tests in `tests/test_scrape.py`**

```python
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from scraper.scrape import main, scrape


def _mock_crawler(raw_matches: list[dict], success: bool = True):
    result = MagicMock()
    result.success = success
    result.extracted_content = json.dumps(raw_matches) if success else None
    result.error_message = "Network error" if not success else ""

    instance = AsyncMock()
    instance.arun.return_value = result
    instance.__aenter__ = AsyncMock(return_value=instance)
    instance.__aexit__ = AsyncMock(return_value=None)
    return instance


RAW = {
    "title": "India vs Australia",
    "date": "2026-06-26",
    "time": "14:00",
    "channels": ["Star Sports 1"],
    "commentators": ["Ravi Shastri"],
    "match_url": "/match/1",
}


async def test_scrape_returns_normalized_matches():
    with patch("scraper.scrape.AsyncWebCrawler") as MockCrawler:
        MockCrawler.return_value = _mock_crawler([RAW])
        matches = await scrape()

    assert len(matches) == 1
    assert matches[0]["title"] == "India vs Australia"
    assert matches[0]["teams"] == ["India", "Australia"]
    assert matches[0]["match_url"] == "https://icdb.tv/match/1"
    assert matches[0]["channels"] == ["Star Sports 1"]


async def test_scrape_exits_on_failure():
    with patch("scraper.scrape.AsyncWebCrawler") as MockCrawler:
        MockCrawler.return_value = _mock_crawler([], success=False)
        with pytest.raises(SystemExit) as exc:
            await scrape()
    assert exc.value.code == 1


async def test_scrape_returns_empty_list_when_no_matches():
    with patch("scraper.scrape.AsyncWebCrawler") as MockCrawler:
        MockCrawler.return_value = _mock_crawler([])
        matches = await scrape()
    assert matches == []


def test_main_dry_run_prints_json_to_stdout(capsys):
    normalized = [{"title": "India vs Australia", "teams": ["India", "Australia"]}]

    with patch("scraper.scrape.asyncio") as mock_asyncio, \
         patch("sys.argv", ["scrape.py", "--dry-run"]):
        mock_asyncio.run.return_value = normalized
        main()

    captured = capsys.readouterr()
    output = json.loads(captured.out)
    assert output["total_matches"] == 1
    assert output["matches"][0]["title"] == "India vs Australia"


def test_main_writes_json_file(tmp_path):
    normalized = [{"title": "India vs Australia", "teams": ["India", "Australia"]}]

    with patch("scraper.scrape.asyncio") as mock_asyncio, \
         patch("scraper.scrape.OUTPUT_PATH", tmp_path / "matches.json"), \
         patch("sys.argv", ["scrape.py"]):
        mock_asyncio.run.return_value = normalized
        main()

    written = json.loads((tmp_path / "matches.json").read_text())
    assert written["total_matches"] == 1
    assert written["source"] == "https://icdb.tv/"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_scrape.py -v
```

Expected: `ModuleNotFoundError: No module named 'scraper.scrape'`

- [ ] **Step 3: Implement `scraper/scrape.py`**

```python
import argparse
import asyncio
import json
import sys
from pathlib import Path

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig
from crawl4ai.extraction_strategy import JsonCssExtractionStrategy

from scraper.normalizer import build_output, normalize_match

SOURCE_URL = "https://icdb.tv/"
OUTPUT_PATH = Path("data/matches.json")

# CSS selectors must be verified against live icdb.tv HTML on first run.
# Open DevTools → Elements, find the repeating match container, and update
# baseSelector and field selectors to match the actual DOM structure.
_SCHEMA = {
    "name": "matches",
    "baseSelector": ".match-row, .fixture-item, tr.match, .match-card",
    "fields": [
        {"name": "title", "selector": ".match-title, .fixture-name, h3, h2", "type": "text"},
        {"name": "date", "selector": ".match-date, .date, time", "type": "text"},
        {"name": "time", "selector": ".match-time, .time, .fixture-time", "type": "text"},
        {"name": "tournament", "selector": ".tournament, .competition, .league", "type": "text"},
        {"name": "venue", "selector": ".venue, .ground, .stadium", "type": "text"},
        {
            "name": "channels",
            "selector": ".channel, .broadcaster, .channel-name",
            "type": "text",
            "multiple": True,
        },
        {
            "name": "commentators",
            "selector": ".commentator, .commenter, .commentator-name",
            "type": "text",
            "multiple": True,
        },
        {"name": "match_url", "selector": "a", "type": "attribute", "attribute": "href"},
    ],
}


async def scrape() -> list[dict]:
    browser_cfg = BrowserConfig(browser_type="chromium", headless=True)
    run_cfg = CrawlerRunConfig(
        wait_for="css:.match-row, .fixture-item, tr.match, .match-card",
        extraction_strategy=JsonCssExtractionStrategy(_SCHEMA),
    )

    async with AsyncWebCrawler(config=browser_cfg) as crawler:
        result = await crawler.arun(url=SOURCE_URL, config=run_cfg)

    if not result.success:
        print(f"ERROR: {result.error_message}", file=sys.stderr)
        sys.exit(1)

    raw = json.loads(result.extracted_content or "[]")
    return [normalize_match(r, SOURCE_URL) for r in raw if r]


def main() -> None:
    parser = argparse.ArgumentParser(description="Scrape match data from icdb.tv")
    parser.add_argument("--dry-run", action="store_true", help="Print JSON to stdout, skip file write")
    args = parser.parse_args()

    matches = asyncio.run(scrape())
    output = build_output(matches, SOURCE_URL)

    if args.dry_run:
        print(json.dumps(output, indent=2, ensure_ascii=False))
        return

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {len(matches)} matches to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_scrape.py -v
```

Expected: all 5 tests PASS.

- [ ] **Step 5: Run the full test suite**

```bash
pytest -v
```

Expected: all 17 tests PASS.

- [ ] **Step 6: Smoke test with --dry-run against live site**

```bash
python -m scraper.scrape --dry-run
```

Expected: JSON printed to stdout with `total_matches > 0`. If `matches` is empty, the CSS selectors need updating — open icdb.tv in Chrome DevTools, find the repeating match element, update `_SCHEMA["baseSelector"]` and the relevant field selectors in `scraper/scrape.py`, then re-run until matches appear.

- [ ] **Step 7: Commit**

```bash
git add tests/test_scrape.py scraper/scrape.py
git commit -m "feat: add crawl4ai scraper and CLI entrypoint with tests"
```

---

### Task 4: GitHub Actions workflow

**Files:**
- Create: `.github/workflows/scrape.yml`

**Interfaces:**
- Consumes: `python -m scraper.scrape` from Task 3, `data/matches.json` from Task 1
- Produces: `data/matches.json` committed to `main` every 5 hours; artifact `matches-<run_id>` retained 30 days

- [ ] **Step 1: Create `.github/workflows/scrape.yml`**

```yaml
name: Scrape icdb.tv matches

on:
  schedule:
    - cron: '0 */5 * * *'
  workflow_dispatch:

permissions:
  contents: write

jobs:
  scrape:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4
        with:
          persist-credentials: true

      - name: Set up Python 3.12
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'
          cache: 'pip'

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Install Playwright browser
        run: crawl4ai-setup

      - name: Run scraper
        run: python -m scraper.scrape

      - name: Commit updated matches
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git diff --quiet data/matches.json || (
            git add data/matches.json &&
            git commit -m "chore: update matches [skip ci]" &&
            git push
          )

      - name: Upload matches artifact
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: matches-${{ github.run_id }}
          path: data/matches.json
          retention-days: 30
```

- [ ] **Step 2: Validate the YAML**

```bash
python -c "import yaml; yaml.safe_load(open('.github/workflows/scrape.yml')); print('valid')"
```

Expected: `valid` (install pyyaml first if needed: `pip install pyyaml`)

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/scrape.yml
git commit -m "feat: add GitHub Actions workflow to scrape every 5 hours"
```

- [ ] **Step 4: Push and trigger a manual run**

```bash
git push origin main
```

Then open `https://github.com/<your-username>/FWCMTRY/actions`, select **Scrape icdb.tv matches**, click **Run workflow**. Verify the run completes, `data/matches.json` is committed, and the artifact appears under the run summary.
