import os
import pytest

from inklink.services.google_docs_service import GoogleDocsService


class FakeExporter:
    def __init__(self, html):
        self._html = html
    def execute(self):
        return self._html


class FakeFiles:
    def __init__(self, html):
        self._html = html
    def export(self, fileId, mimeType):
        return FakeExporter(self._html)


class FakeDriveService:
    def __init__(self, html):
        self._html = html
    def files(self):
        return FakeFiles(self._html)


@pytest.fixture(autouse=True)
def disable_auth(monkeypatch):
    # Disable actual Google OAuth flow
    monkeypatch.setattr(GoogleDocsService, '_authenticate', lambda self: None)
    yield


def test_extract_doc_id():
    service = GoogleDocsService()
    url = 'https://docs.google.com/document/d/ABC12345/edit?usp=sharing'
    assert service._extract_doc_id(url) == 'ABC12345'
    # ID unchanged
    assert service._extract_doc_id('XYZ') == 'XYZ'


def test_fetch_success(monkeypatch):
    html = (
        '<html><head><title>Doc Title</title></head><body>'
        '<h1>Heading</h1>'
        '<p>Paragraph text</p>'
        '<ul><li>Item1</li><li>Item2</li></ul>'
        '<pre>code</pre>'
        '<img src="http://img.png" alt="Alt Text"/>'
        '</body></html>'
    )
    service = GoogleDocsService()
    # Inject fake drive service
    service.drive_service = FakeDriveService(html)
    result = service.fetch('DOCID')
    # Title from HTML
    assert result['title'] == 'Doc Title'
    types = [item['type'] for item in result['structured_content']]
    assert 'h1' in types
    assert 'paragraph' in types
    assert 'list' in types
    assert 'code' in types
    assert 'image' in types
    # Images list
    assert isinstance(result['images'], list)
    assert result['images'][0]['url'] == 'http://img.png'
    assert result['images'][0]['caption'] == 'Alt Text'


def test_fetch_error(monkeypatch):
    # Simulate export failure
    class ErrDrive:
        def files(self):
            raise RuntimeError('fail')
    service = GoogleDocsService()
    service.drive_service = ErrDrive()
    result = service.fetch('BADID')
    assert result['title'] == 'BADID'
    assert any('Could not fetch Google Docs doc BADID' in item.get('content', '')
               for item in result['structured_content'])
    assert result['images'] == []