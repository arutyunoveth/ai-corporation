from __future__ import annotations

from src.modules.tender_connectors.text_extraction import (
    quality_gate_text,
    extract_attachment_urls,
    extract_text_from_attachment_bytes,
)


class TestQualityGate:
    def test_accepts_valid_text(self):
        result = quality_gate_text("Поставка картриджей HP для офисной техники в количестве 50 штук")
        assert result.accepted is True
        assert result.reason == "accepted"

    def test_rejects_empty(self):
        result = quality_gate_text("")
        assert result.accepted is False
        assert result.reason == "empty"

    def test_rejects_none(self):
        result = quality_gate_text(None)
        assert result.accepted is False

    def test_rejects_too_short(self):
        result = quality_gate_text("короткий")
        assert result.accepted is False
        assert result.reason == "too_short"

    def test_rejects_noise_only(self):
        result = quality_gate_text("!@#$%^&*()_+" * 10)
        assert result.accepted is False

    def test_rejects_repetitive_noise(self):
        result = quality_gate_text("а " * 50)
        assert result.accepted is False


class TestExtractUrls:
    def test_finds_direct_urls(self):
        urls = extract_attachment_urls({
            "attachments": [{"url": "https://example.com/doc.pdf"}],
        })
        assert "https://example.com/doc.pdf" in urls

    def test_finds_urls_in_text(self):
        urls = extract_attachment_urls({
            "description": "Скачать: https://example.com/file.txt",
        })
        assert len(urls) == 1

    def test_deduplicates(self):
        urls = extract_attachment_urls({
            "files": [
                {"url": "https://example.com/a.pdf"},
                {"url": "https://example.com/a.pdf"},
            ],
        })
        assert len(urls) == 1

    def test_returns_empty_for_no_urls(self):
        assert extract_attachment_urls({"name": "test"}) == []


class TestExtractBytes:
    def test_txt_utf8(self):
        text = extract_text_from_attachment_bytes("file.txt", "Привет мир".encode("utf-8"))
        assert text == "Привет мир"

    def test_txt_cp1251(self):
        text = extract_text_from_attachment_bytes("file.txt", "Тест".encode("cp1251"))
        assert text == "Тест"

    def test_unknown_extension(self):
        text = extract_text_from_attachment_bytes("file.bin", b"hello world")
        assert text == "hello world"

    def test_empty_content(self):
        text = extract_text_from_attachment_bytes("file.txt", b"")
        assert text is None or text == ""
