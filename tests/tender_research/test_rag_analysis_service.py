from __future__ import annotations

from dataclasses import dataclass
from unittest.mock import MagicMock, patch

from src.tender_research.rag.analysis_service import (
    _build_report_markdown,
    _slugify,
    _vector_store_path,
    analyze_tender,
)
from src.tender_research.rag.retriever import RagSearchHit
from src.tender_research.rag.schemas import (
    ANALYSIS_SECTIONS,
    TenderAnalysisSection,
)


class TestSlugify:
    def test_simple(self):
        assert _slugify("Hello World") == "hello_world"

    def test_special_chars(self):
        assert _slugify("qwen2.5-14b") == "qwen2_5_14b"

    def test_empty(self):
        assert _slugify("") == "default"


class TestVectorStorePath:
    def test_default_format(self):
        class FakeConfig:
            rag_vector_store_path = "{provider}_{model}.json"
            data_dir = "/tmp"
            rag_embeddings_provider = "hashing"
        path = _vector_store_path(FakeConfig(), provider_name="hash", model_name="local-hash-v1")
        assert path.endswith("hash_local_hash_v1.json") or "hash_local_hash_v1" in path

    def test_default_path_when_no_format(self):
        class FakeConfig:
            rag_vector_store_path = None
            data_dir = "/tmp"
            rag_embeddings_provider = "hashing"
        path = _vector_store_path(FakeConfig(), provider_name="hash", model_name="local-hash-v1")
        assert "vector_store" in path


class TestBuildReportMarkdown:
    def test_empty_sections(self):
        result = _build_report_markdown(
            registry_number="123",
            sections=[],
            used_llm=False,
            llm_model=None,
            retrieval_provider="hash",
            retrieval_model="v1",
        )
        assert "123" in result
        assert "0" in result

    def test_section_with_answer_and_sources(self):
        sections = [
            TenderAnalysisSection(
                id="01_notice_info",
                title="Информация об извещении",
                question="Тестовый вопрос",
                answer="Тестовый ответ",
                sources=[],
                status="completed",
            )
        ]
        result = _build_report_markdown(
            registry_number="123",
            sections=sections,
            used_llm=True,
            llm_model="qwen-test",
            retrieval_provider="hash",
            retrieval_model="v1",
        )
        assert "01_notice_info" in result
        assert "Тестовый ответ" in result
        assert "qwen-test" in result

    def test_insufficient_context(self):
        sections = [
            TenderAnalysisSection(
                id="01_notice_info",
                title="Информация об извещении",
                question="Тестовый вопрос",
                answer="",
                sources=[],
                status="insufficient_context",
            )
        ]
        result = _build_report_markdown("123", sections, True, "qwen", "hash", "v1")
        assert "Недостаточно контекста" in result

    def test_no_context(self):
        sections = [
            TenderAnalysisSection(
                id="01_notice_info",
                title="Информация об извещении",
                question="Тестовый вопрос",
                answer="",
                sources=[],
                status="no_context",
            )
        ]
        result = _build_report_markdown("123", sections, False, None, "hash", "v1")
        assert "Нет документов для анализа" in result


class TestAnalyzeTender:
    def test_no_tender_found(self):
        with patch(
            "src.tender_research.rag.analysis_service._get_session"
        ) as mock_session:
            mock_repo = MagicMock()
            mock_repo.get_tender_by_registry_number.return_value = None
            mock_repo.get_tender_by_external.return_value = None
            with patch(
                "src.tender_research.rag.analysis_service.TenderRepository",
                return_value=mock_repo,
            ):
                result = analyze_tender(
                    registry_number="nonexistent-123",
                    session=MagicMock(),
                )
                assert result.status == "no_context"
                assert "not found" in " ".join(result.errors).lower()

    def test_no_embeddings(self):
        with patch(
            "src.tender_research.rag.analysis_service._get_session"
        ) as mock_session:
            mock_repo = MagicMock()
            mock_repo.get_tender_by_registry_number.return_value = MagicMock()
            mock_repo.get_tender_by_external.return_value = MagicMock()
            mock_repo.count_document_embeddings.return_value = 0
            with patch(
                "src.tender_research.rag.analysis_service.TenderRepository",
                return_value=mock_repo,
            ):
                result = analyze_tender(
                    registry_number="123",
                    provider="hashing",
                    model="local-hash-v1",
                    session=MagicMock(),
                )
                assert result.status == "no_context"
                assert any("embeddings" in e.lower() for e in result.errors)

    def test_retrieval_only_mode(self):
        mock_tender = MagicMock()
        mock_tender.title = "Test Tender"

        mock_repo = MagicMock()
        mock_repo.get_tender_by_registry_number.return_value = mock_tender
        mock_repo.get_tender_by_external.return_value = mock_tender
        mock_repo.count_document_embeddings.return_value = 10

        mock_emb_provider = MagicMock()
        mock_emb_provider.provider_name = "hashing"
        mock_emb_provider.model_name = "local-hash-v1"
        mock_emb_provider.dimension = 8

        mock_vector_store = MagicMock()

        mock_retriever = MagicMock()
        mock_retriever.search_documents.return_value = []

        with patch(
            "src.tender_research.rag.analysis_service._get_session"
        ) as mock_session:
            with patch(
                "src.tender_research.rag.analysis_service.TenderRepository",
                return_value=mock_repo,
            ):
                with patch(
                    "src.tender_research.rag.analysis_service.build_embedding_provider",
                    return_value=mock_emb_provider,
                ):
                    with patch(
                        "src.tender_research.rag.analysis_service.JsonVectorStore",
                        return_value=mock_vector_store,
                    ):
                        with patch(
                            "src.tender_research.rag.analysis_service.RagRetriever",
                            return_value=mock_retriever,
                        ):
                            result = analyze_tender(
                                registry_number="123",
                                provider="hashing",
                                model="local-hash-v1",
                                session=MagicMock(),
                                use_llm=False,
                            )
                            assert result.status in (
                                "completed",
                                "completed_with_warnings",
                            )
                            assert result.sections_count == len(ANALYSIS_SECTIONS)
                            assert result.registry_number == "123"

    def test_with_search_hits_retrieval_only(self):
        mock_tender = MagicMock()
        mock_repo = MagicMock()
        mock_repo.get_tender_by_registry_number.return_value = mock_tender
        mock_repo.get_tender_by_external.return_value = mock_tender
        mock_repo.count_document_embeddings.return_value = 10

        mock_emb_provider = MagicMock()
        mock_emb_provider.provider_name = "hashing"
        mock_emb_provider.model_name = "local-hash-v1"
        mock_emb_provider.dimension = 8

        mock_vector_store = MagicMock()
        mock_retriever = MagicMock()

        hit = RagSearchHit(
            chunk_id="chunk-1",
            score=0.95,
            registry_number="123",
            tender_id="tender-1",
            tender_title="Test Tender",
            customer_name="Test Customer",
            document_id="doc-1",
            file_name="test.pdf",
            chunk_index=0,
            preview="Test preview content...",
            text="Test content for retrieval only mode.",
        )
        mock_retriever.search_documents.return_value = [hit]

        with patch(
            "src.tender_research.rag.analysis_service._get_session"
        ) as mock_session:
            with patch(
                "src.tender_research.rag.analysis_service.TenderRepository",
                return_value=mock_repo,
            ):
                with patch(
                    "src.tender_research.rag.analysis_service.build_embedding_provider",
                    return_value=mock_emb_provider,
                ):
                    with patch(
                        "src.tender_research.rag.analysis_service.JsonVectorStore",
                        return_value=mock_vector_store,
                    ):
                        with patch(
                            "src.tender_research.rag.analysis_service.RagRetriever",
                            return_value=mock_retriever,
                        ):
                            result = analyze_tender(
                                registry_number="123",
                                provider="hashing",
                                model="local-hash-v1",
                                session=MagicMock(),
                                use_llm=False,
                            )
                            assert result.status in (
                                "completed",
                                "completed_with_warnings",
                            )
                            assert result.sections_count == len(ANALYSIS_SECTIONS)
                            assert any(
                                s.status == "retrieval_only"
                                for s in result.sections
                            )

    def test_report_saving(self):
        mock_tender = MagicMock()
        mock_repo = MagicMock()
        mock_repo.get_tender_by_registry_number.return_value = mock_tender
        mock_repo.get_tender_by_external.return_value = mock_tender
        mock_repo.count_document_embeddings.return_value = 10

        mock_emb_provider = MagicMock()
        mock_emb_provider.provider_name = "hashing"
        mock_emb_provider.model_name = "local-hash-v1"
        mock_emb_provider.dimension = 8

        mock_vector_store = MagicMock()
        mock_retriever = MagicMock()
        mock_retriever.search_documents.return_value = []

        with patch(
            "src.tender_research.rag.analysis_service._get_session"
        ) as mock_session:
            with patch(
                "src.tender_research.rag.analysis_service.TenderRepository",
                return_value=mock_repo,
            ):
                with patch(
                    "src.tender_research.rag.analysis_service.build_embedding_provider",
                    return_value=mock_emb_provider,
                ):
                    with patch(
                        "src.tender_research.rag.analysis_service.JsonVectorStore",
                        return_value=mock_vector_store,
                    ):
                        with patch(
                            "src.tender_research.rag.analysis_service.RagRetriever",
                            return_value=mock_retriever,
                        ):
                            with patch(
                                "src.tender_research.rag.analysis_service._save_report"
                            ) as mock_save:
                                mock_save.return_value = "/tmp/report.md"
                                result = analyze_tender(
                                    registry_number="123",
                                    provider="hashing",
                                    model="local-hash-v1",
                                    session=MagicMock(),
                                    use_llm=False,
                                    save_report=True,
                                )
                                assert result.report_path is not None
                                mock_save.assert_called_once()
