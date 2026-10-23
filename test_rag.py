import pytest
from pathlib import Path
import config
from ingest import extract_pages_from_pdf, chunk_pages, index_chunks
from rag import EvidenceRetriever, RAGAssistant, get_retriever


def test_pdf_extraction_and_page_count():
    """Verify that the supplied PDF has 87 pages and all are extracted."""
    assert config.PDF_PATH.exists(), "Supplied PDF must exist in data directory"
    pages = extract_pages_from_pdf(config.PDF_PATH)
    assert len(pages) == 87, f"Expected 87 pages, extracted {len(pages)}"
    assert all("page_number" in p and "chapter" in p for p in pages)


def test_chunking_metadata():
    """Verify that chunking retains page numbers, chapter, and section."""
    pages = extract_pages_from_pdf(config.PDF_PATH)
    chunks = chunk_pages(pages[:5])
    assert len(chunks) > 0
    for chunk in chunks:
        meta = chunk["metadata"]
        assert "page_number" in meta
        assert "chapter" in meta
        assert "section" in meta
        assert meta["page_number"] >= 1


def test_retrieval_relevance():
    """Verify that relevant questions retrieve relevant chunks."""
    retriever = get_retriever()
    if not retriever.is_ready():
        pytest.skip("ChromaDB is not yet initialized.")
    
    # Query about copyright extension
    results = retriever.retrieve("How long does a proprietor have copyright in a registered design, and can it be extended?", top_k=2)
    assert len(results) > 0
    combined_text = " ".join([r["text"] for r in results]).lower()
    # Should find references to ten years or extension of five years
    assert "ten years" in combined_text or "extended" in combined_text or "copyright" in combined_text


def test_mock_rag_supported_answer(monkeypatch):
    """Test RAG flow when model generates supported answer with citations."""
    assistant = RAGAssistant(api_key="mock_key")
    
    mock_passages = [{
        "text": "The proprietor shall have copyright in the design for ten years from the date of registration. This period of ten years can be extended by five years.",
        "metadata": {"chapter": "Chapter 6", "section": "06.04", "page_number": 36},
        "similarity": 0.85
    }]
    monkeypatch.setattr(assistant.retriever, "is_ready", lambda: True)
    monkeypatch.setattr(assistant.retriever, "retrieve", lambda q, top_k=4: mock_passages)
    
    class MockResponse:
        text = "A proprietor has copyright for ten years, extendable by five years.\nSource: Chapter 6, Section 06.04, Page 36"
    
    class MockModelsService:
        def generate_content(self, *args, **kwargs):
            return MockResponse()

    class MockClient:
        def __init__(self, *args, **kwargs):
            self.models = MockModelsService()

    assistant.client = MockClient()

    result = assistant.answer_question("How long does a proprietor have copyright?")
    assert result["status"] == "supported"
    assert "ten years" in result["answer"].lower()
    assert result["answer"] != "Not found"


def test_mock_rag_unsupported_not_found(monkeypatch):
    """Test strict 'Not found' behavior for out-of-scope question."""
    assistant = RAGAssistant(api_key="mock_key")
    monkeypatch.setattr(assistant.retriever, "is_ready", lambda: True)
    monkeypatch.setattr(assistant.retriever, "retrieve", lambda q, top_k=4: [{
        "text": "Unrelated chapter text",
        "metadata": {"chapter": "Chapter 1", "section": "01.01", "page_number": 5},
        "similarity": 0.2
    }])

    class MockResponse:
        text = "Not found"

    class MockModelsService:
        def generate_content(self, *args, **kwargs):
            return MockResponse()

    class MockClient:
        def __init__(self, *args, **kwargs):
            self.models = MockModelsService()

    assistant.client = MockClient()

    result = assistant.answer_question("What is the government fee to register a trademark?")
    assert result["answer"] == "Not found"
    assert result["status"] == "not_found"
