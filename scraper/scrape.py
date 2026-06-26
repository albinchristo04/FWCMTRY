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

_SCHEMA = {
    "name": "matches",
    "baseSelector": ".match-row",
    "fields": [
        {"name": "title", "selector": ".col-match a", "type": "text"},
        {"name": "datetime", "selector": ".col-date .local-time", "type": "text"},
        {"name": "tournament", "selector": ".col-comp", "type": "text"},
        {"name": "channels", "selector": ".col-chan", "type": "text"},
        {"name": "commentators", "selector": ".col-contrib", "type": "text"},
        {"name": "match_url", "selector": ".col-match a", "type": "attribute", "attribute": "href"},
    ],
}


async def scrape() -> list[dict]:
    browser_cfg = BrowserConfig(browser_type="chromium", headless=True)
    run_cfg = CrawlerRunConfig(
        wait_for="css:#resultsdata",
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
