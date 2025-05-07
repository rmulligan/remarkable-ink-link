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
        b" ftp://leading-scheme.com",  # wrong scheme
        b"https://trailing-space.com ",  # trailing space
        b"http:// no-host",  # space after scheme
        # New invalid patterns
        b"htt://example.com",  # invalid scheme typo
        b"http://",  # missing netloc
        # b"https://example.com<evil>",     # invalid character '<' (prefix stripping handled separately)
        b"https://example.com|bar",  # invalid character '|'
        b"https://example.com'quote",  # invalid character: single quote
        b'https://example.com"double',  # invalid character: double quote
        b"https://example.com`backtick",  # invalid character: backtick
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


def test_extract_url_prefix_strips_invalid_suffix():
    # Valid URL prefix followed by invalid '<' character and text
    payload = b"https://example.com/page<evil>"
    assert call_extract(payload) == "https://example.com/page"


@pytest.mark.parametrize(
    "payload, expected",
    [
        (b"https://site.org/foo^bar", "https://site.org/foo"),
    ],
)
def test_extract_url_prefix_various(payload, expected):
    assert call_extract(payload) == expected


@pytest.mark.parametrize(
    "payload, expected",
    [
        # Mixed valid/invalid content with strippable suffixes
        (
            b"https://example.com/valid<script>alert(1)</script>",
            "https://example.com/valid",
        ),
        (b"https://example.org/path^remainder_ignored", "https://example.org/path"),
        (b"http://test.com/page^with^multiple^carets", "http://test.com/page"),
        (
            b"https://github.com/repo/issue#123<click>here</click>",
            "https://github.com/repo/issue#123",
        ),
        # Mixed content with multiple delimiters where only the first should be used
        (
            b"https://api.site.com/v1/endpoint<param>^version=2",
            "https://api.site.com/v1/endpoint",
        ),
        (b"https://example.com^suffix<another>", "https://example.com"),
        # Edge cases with valid URLs that end with allowed special chars
        (
            b"https://example.com/search?q=test&limit=10<more>",
            "https://example.com/search?q=test&limit=10",
        ),
        (
            b"https://sub.domain.org/path/123-456_789^invalid",
            "https://sub.domain.org/path/123-456_789",
        ),
        # Valid URLs with fragments and query parameters followed by invalid content
        (
            b"https://site.com/path?param=value#fragment<inject>",
            "https://site.com/path?param=value#fragment",
        ),
        (
            b"http://api.example.org/?q=search+term&page=1^sort=desc",
            "http://api.example.org/?q=search+term&page=1",
        ),
    ],
)
def test_extract_url_mixed_content(payload, expected):
    """Test extraction of valid URLs from mixed valid/invalid content.

    This test focuses specifically on the URL handler's ability to:
    1. Extract valid URL prefixes from strings containing both valid and invalid content
    2. Correctly handle different types of delimiting characters (< and ^)
    3. Process complex URLs with query parameters and fragments mixed with invalid content
    4. Handle edge cases with multiple delimiters or special characters
    """
    assert call_extract(payload) == expected
