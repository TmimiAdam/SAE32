"""Tests for advanced search features."""

import pytest

from src import server
from src.web_server import app


def test_text_matches_boolean_and():
    """Boolean AND should require both terms in the same text unit."""
    spec = server.parse_search_query("adam and optimization")
    assert server.text_matches("Adam is a popular optimization algorithm.", spec)
    assert not server.text_matches("Adam is popular.", spec)


def test_text_matches_boolean_or():
    """Boolean OR should accept either term."""
    spec = server.parse_search_query("bonjour ou adam")
    assert server.text_matches("Bonjour, ceci est un test.", spec)
    assert server.text_matches("Adam is a popular optimization algorithm.", spec)
    assert not server.text_matches("Rien a voir ici.", spec)


def test_text_matches_regex():
    """Regex mode should use the provided pattern."""
    spec = server.parse_search_query(r"Bonj.*test", use_regex=True)
    assert server.text_matches("Bonjour, ceci est un fichier de test.", spec)
    assert not server.text_matches("Adam is a popular optimization algorithm.", spec)


def test_perform_structured_search_supports_boolean_and():
    """The structured search should expose boolean matches in project data."""
    results = server.perform_structured_search("adam and optimization", types=["html"])
    assert results
    assert any(hit["type"] == "html" for hit in results)


def test_perform_structured_search_supports_boolean_or():
    """OR queries should match multiple files in project data."""
    results = server.perform_structured_search("bonjour or adam", types=["txt", "html"])
    assert results
    assert any(hit["file"] == "test.txt" for hit in results)
    assert any(hit["file"] == "adam.html" for hit in results)


def test_perform_structured_search_supports_regex_prefix():
    """The regex prefix should work even outside the web UI."""
    results = server.perform_structured_search(r"re:Bonj.*test", types=["txt"])
    assert results
    assert results[0]["file"] == "test.txt"


def test_invalid_regex_is_rejected():
    """Invalid regex patterns should raise a clear validation error."""
    with pytest.raises(ValueError):
        server.perform_structured_search(r"re:[", types=["txt"])


def test_invalid_boolean_query_is_rejected():
    """Invalid boolean syntax should raise a validation error."""
    with pytest.raises(ValueError):
        server.perform_structured_search("adam and or optimization", types=["html"])


def test_web_api_accepts_regex_flag():
    """The web API should pass the regex flag to the search engine."""
    client = app.test_client()
    response = client.get("/api/search?q=Bonj.*test&types=txt&regex=1")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["count"] >= 1
    assert payload["results"][0]["file"] == "test.txt"


def test_web_api_rejects_invalid_regex():
    """Invalid regex patterns should return a client error."""
    client = app.test_client()
    response = client.get("/api/search?q=[&types=txt&regex=1")

    assert response.status_code == 400
    payload = response.get_json()
    assert "Invalid regex" in payload["error"]


def test_web_api_rejects_invalid_boolean_query():
    """Invalid boolean syntax should also return a client error."""
    client = app.test_client()
    response = client.get("/api/search?q=adam%20and%20or%20optimization&types=html")

    assert response.status_code == 400
    payload = response.get_json()
    assert "invalid" in payload["error"].lower()
