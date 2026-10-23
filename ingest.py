import re
from pathlib import Path
from typing import List, Dict, Any
import pypdf
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
import chromadb

import config


def get_embedding_function():
    """Returns local HuggingFace embedding function using sentence-transformers."""
    return HuggingFaceEmbeddings(
        model_name=config.EMBEDDING_MODEL_NAME,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True}
    )


# Official Table of Contents mapping for exact chapter determination
CHAPTER_PAGE_RANGES = [
    (1, 1, "Title"),
    (2, 2, "Contents"),
    (3, 4, "Preface"),
    (5, 6, "Chapter 1 – Introduction"),
    (7, 10, "Chapter 2 – Important definitions"),
    (11, 23, "Chapter 3 – Filing of Design Application"),
    (24, 33, "Chapter 4 – Examination and registration of designs"),
    (34, 34, "Chapter 5 – Patent Office Journal"),
    (35, 36, "Chapter 6 – Piracy of registered designs and consequences thereof"),
    (37, 44, "Chapter 7 – Post registration procedures"),
    (45, 46, "Chapter 8 – Transfer of rights"),
    (47, 49, "Chapter 9 – General Services"),
    (50, 50, "Chapter 10 – Use and acquisition of registered design by Government"),
    (51, 53, "Chapter 11 – General powers of Controller"),
    (54, 57, "Chapter 12 – Evidences etc."),
    (58, 59, "Chapter 13 – Restrictive conditions in contract etc."),
    (60, 60, "Chapter 14 – Appeals"),
    (61, 62, "Chapter 15 – Requirements before delivery on sales"),
    (63, 64, "Chapter 16 – Timelines"),
    (65, 85, "Annexure I – Important Case Laws"),
    (86, 87, "Annexure II – Specimen novelty statements & disclaimers in representation sheet"),
]


def get_chapter_for_page(page_num: int) -> str:
    """Returns official chapter name based on page range."""
    for start, end, name in CHAPTER_PAGE_RANGES:
        if start <= page_num <= end:
            return name
    return "Manual of Designs Practice & Procedure"


def extract_pages_from_pdf(pdf_path: Path) -> List[Dict[str, Any]]:
    """
    Extracts text from all pages of the supplied PDF.
    Preserves original page numbers, chapters, and sections.
    """
    if not pdf_path.exists():
        raise FileNotFoundError(
            f"PDF file not found at {pdf_path}. Please place the official "
            f"'Manual of Designs Practice & Procedure' PDF into the data/ folder."
        )

    reader = pypdf.PdfReader(str(pdf_path))
    total_pages = len(reader.pages)
    print(f"[INFO] Loaded PDF with {total_pages} total pages.")

    pages_data = []

    for idx, page in enumerate(reader.pages):
        page_num = idx + 1  # 1-indexed
        raw_text = page.extract_text() or ""
        clean_text = raw_text.strip()

        if not clean_text:
            print(f"[WARNING] Page {page_num} has no extractable text.")
            continue

        chapter_name = get_chapter_for_page(page_num)

        pages_data.append({
            "page_number": page_num,
            "chapter": chapter_name,
            "text": clean_text
        })

    print(f"[INFO] Extracted text from {len(pages_data)} of {total_pages} pages.")
    return pages_data


def chunk_pages(pages_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Splits page text into overlapping chunks, maintaining page, chapter,
    and section metadata.
    """
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=config.CHUNK_SIZE,
        chunk_overlap=config.CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""]
    )

    chunks = []

    for page in pages_data:
        page_num = page["page_number"]
        chapter = page["chapter"]
        page_text = page["text"]

        splits = text_splitter.split_text(page_text)

        for chunk_idx, split_text in enumerate(splits):
            # Extract section numbers like '06.04', '03.06.02.06', 'Section 11' if present
            section_match = re.search(r"(\b\d{2}\.\d{2}(?:\.\d{2})*\b|Section\s+\d+(?:\([0-9a-zA-Z]+\))*)", split_text)
            section = section_match.group(0) if section_match else "General"

            chunk_id = f"doc_p{page_num}_c{chunk_idx+1}"

            chunks.append({
                "id": chunk_id,
                "text": split_text,
                "metadata": {
                    "source": "Manual of Designs Practice & Procedure",
                    "page_number": int(page_num),
                    "chapter": str(chapter),
                    "section": str(section),
                    "chunk_id": chunk_id
                }
            })

    print(f"[INFO] Created {len(chunks)} chunks across {len(pages_data)} pages.")
    return chunks


def index_chunks(chunks: List[Dict[str, Any]], force_reindex: bool = False):
    """
    Embeds and stores chunks into ChromaDB persistently.
    Avoids duplicate indexing unless force_reindex=True.
    """
    client = chromadb.PersistentClient(path=str(config.CHROMA_DIR))

    # Check if collection already exists
    existing_collections = [c.name for c in client.list_collections()]
    if config.COLLECTION_NAME in existing_collections:
        if force_reindex:
            print(f"[INFO] Deleting existing collection '{config.COLLECTION_NAME}' for clean reindex.")
            client.delete_collection(config.COLLECTION_NAME)
            collection = client.create_collection(
                name=config.COLLECTION_NAME,
                metadata={"hnsw:space": "cosine"}
            )
        else:
            collection = client.get_collection(config.COLLECTION_NAME)
            count = collection.count()
            if count > 0:
                print(f"[INFO] Collection '{config.COLLECTION_NAME}' already has {count} documents. Skipping re-indexing.")
                return collection
    else:
        collection = client.create_collection(
            name=config.COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"}
        )

    print(f"[INFO] Generating embeddings with {config.EMBEDDING_MODEL_NAME}...")
    embedding_func = get_embedding_function()

    # Batch insert into ChromaDB
    batch_size = 64
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i + batch_size]
        texts = [b["text"] for b in batch]
        ids = [b["id"] for b in batch]
        metadatas = [b["metadata"] for b in batch]

        embeddings = embedding_func.embed_documents(texts)
        collection.add(
            documents=texts,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids
        )
        print(f"[INFO] Indexed chunks {i+1} to {min(i+batch_size, len(chunks))}...")

    print(f"[SUCCESS] ChromaDB indexed successfully. Total items: {collection.count()}")
    return collection


def run_ingestion(force_reindex: bool = False):
    """Master ingestion function to process PDF and build vector database."""
    print("=== Starting PDF Ingestion Pipeline ===")
    pages = extract_pages_from_pdf(config.PDF_PATH)
    chunks = chunk_pages(pages)
    collection = index_chunks(chunks, force_reindex=force_reindex)
    print("=== PDF Ingestion Complete ===")
    return collection


if __name__ == "__main__":
    run_ingestion(force_reindex=True)
