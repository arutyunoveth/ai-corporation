import tempfile
from pathlib import Path

from src.tender_research.document_text_extractor import extract_text


def test_txt_extraction():
    with tempfile.NamedTemporaryFile(suffix=".txt", mode="w", delete=False) as f:
        f.write("Hello world\nTest line 2")
        path = f.name
    status, text = extract_text(path)
    assert status == "extracted"
    assert "Hello world" in text
    Path(path).unlink()


def test_unsupported_extension():
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
        f.write(b"fake-image-data")
        path = f.name
    status, text = extract_text(path)
    assert status == "unsupported"
    Path(path).unlink()


def test_empty_file():
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
        path = f.name
    status, text = extract_text(path)
    assert status == "empty"
    assert text == ""
    Path(path).unlink()
