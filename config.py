import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
PDF_PATH = DATA_DIR / "manual_of_designs_practice_and_procedure.pdf"
CHROMA_DIR = BASE_DIR / "chroma_db"
COLLECTION_NAME = "designs_law_collection"

# Embeddings model name (lightweight, runs completely local on CPU)
EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

# Chunking parameters
CHUNK_SIZE = 800
CHUNK_OVERLAP = 150

# Retrieval parameters
TOP_K = 4

# Gemini API configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "") or os.getenv("GOOGLE_API_KEY", "")
GEMINI_MODEL_NAME = "gemini-3.5-flash-lite"
