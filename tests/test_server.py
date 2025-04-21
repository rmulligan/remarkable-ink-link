import pytest

from inklink.server import URLHandler


def call_extract(payload: bytes):
    # Instantiate without full HTTPServer setup
    handler = URLHandler.__new__(URLHandler)
    return URLHandler._extract_url(handler, payload)


@pytest.mark.parametrize(
    "payload, expected",
    [
        (b"https://example.com", "https://example.com"),
        (b"http://foo.bar/path?query=1#frag", "http://foo.bar/path?query=1#frag"),
    ],
)
def test_extract_url_valid_plain(payload, expected):
    assert call_extract(payload) == expected


@pytest.mark.parametrize(
    "payload",
    [
        # Existing invalid patterns
        b"https://good.com\nmalicious",  # contains newline
        b" ftp://leading-scheme.com",      # wrong scheme
        b"https://trailing-space.com ",    # trailing space
        b"http:// no-host",                # space after scheme
        # New invalid patterns
        b"htt://example.com",              # invalid scheme typo
        b"http://",                       # missing netloc
        b"https://example.com<evil>",     # invalid character '<'
        b"https://example.com|bar",       # invalid character '|'
        b'https://example.com\'quote',     # invalid character: single quote
        b'https://example.com"double',      # invalid character: double quote
        b"https://example.com`backtick",    # invalid character: backtick
    ],
)
def test_extract_url_invalid_plain(payload):
    assert call_extract(payload) is None


def test_extract_url_valid_json():
    json_payload = b'{"url": "https://json.example.com/test"}'
    assert call_extract(json_payload) == "https://json.example.com/test"


def test_extract_url_invalid_json():
    json_payload = b'{"url": "https://bad.com\nbad"}'
    assert call_extract(json_payload) is None
