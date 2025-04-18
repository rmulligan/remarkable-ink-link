import requests
from types import SimpleNamespace
import pytest

from inklink.services.web_scraper_service import WebScraperService

@pytest.fixture(autouse=True)
def disable_network(monkeypatch):
    # Prevent real HTTP calls
    monkeypatch.setattr(requests, 'get', lambda url, timeout=10: SimpleNamespace(
        text="", status_code=200, raise_for_status=lambda: None
    ))
    yield

def test_scrape_basic(monkeypatch):
    html = (
        "<html><head>"
        "<title>Test Page</title>"
        "<meta property='og:title' content='OG Title'></head>"
        "<body>"
        "<h1>Heading</h1>"
        "<p>Paragraph text</p>"
        "<ul><li>Item1</li><li>Item2</li></ul>"
        "<pre>code block</pre>"
        "</body></html>"
    )
    # Fake the GET response
    def fake_get(url, timeout):
        return SimpleNamespace(
            text=html,
            status_code=200,
            raise_for_status=lambda: None
        )
    monkeypatch.setattr(requests, 'get', fake_get)
    service = WebScraperService()
    result = service.scrape("http://example.com")
    assert result["title"] == "OG Title"
    types = [item["type"] for item in result["structured_content"]]
    # Should find at least one of each type
    assert "h1" in types
    assert "paragraph" in types
    assert "list" in types
    assert "code" in types

def test_scrape_fallback_on_error(monkeypatch):
    # Simulate network error
    def fake_get(url, timeout):
        raise requests.ConnectionError("fail")
    monkeypatch.setattr(requests, 'get', fake_get)
    service = WebScraperService()
    result = service.scrape("http://example.com")
    assert result["title"] == "http://example.com"
    assert any("Could not fetch content" in item.get('content', '')
               for item in result["structured_content"])