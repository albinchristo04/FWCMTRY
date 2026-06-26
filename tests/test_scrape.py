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
