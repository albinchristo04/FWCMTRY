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
