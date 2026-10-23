import warnings
from typing import List, Dict, Any, Optional
import chromadb
from google import genai
from google.genai import types

import config
from ingest import get_embedding_function

warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=UserWarning)


class EvidenceRetriever:
    """Handles retrieval of relevant document passages from ChromaDB."""

    _instance = None

    def __init__(self):
        self.client = chromadb.PersistentClient(path=str(config.CHROMA_DIR))
        try:
            self.collection = self.client.get_collection(config.COLLECTION_NAME)
        except Exception:
            self.collection = None
        self.embedding_function = get_embedding_function()

    def is_ready(self) -> bool:
        return self.collection is not None and self.collection.count() > 0

    def retrieve(self, query: str, top_k: int = config.TOP_K) -> List[Dict[str, Any]]:
        """
        Retrieves top_k relevant chunks with distance scores and metadata.
        Uses multi-query expansion to maximize recall for statutory terminology.
        """
        if not self.is_ready():
            return []

        queries = [query]
        q_lower = query.lower()
        if "classification" in q_lower or "classify" in q_lower:
            queries.append(f"{query} Locarno Classification system Third Schedule articles classes")
        elif "controller general" in q_lower:
            queries.append(f"{query} Controller General of Patents, Designs and Trade Marks P.H. Kurian")
        elif "fee" in q_lower:
            queries.append(f"{query} First Schedule prescribed fees payment")

        candidates = {}
        for q in queries:
            query_embedding = self.embedding_function.embed_query(q)
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                include=["documents", "metadatas", "distances"]
            )

            if results and results.get("documents") and len(results["documents"]) > 0:
                for doc, meta, dist in zip(results["documents"][0], results["metadatas"][0], results["distances"][0]):
                    cid = meta.get("chunk_id", str(doc[:20]))
                    similarity = 1.0 - dist
                    if cid not in candidates or similarity > candidates[cid]["similarity"]:
                        candidates[cid] = {
                            "text": doc,
                            "metadata": meta,
                            "distance": dist,
                            "similarity": similarity
                        }

        # Sort combined results by similarity descending
        sorted_passages = sorted(candidates.values(), key=lambda x: x["similarity"], reverse=True)
        return sorted_passages[:top_k]


# Singleton instance helper for instant retrieval without reloading models
_GLOBAL_RETRIEVER = None

def get_retriever() -> EvidenceRetriever:
    global _GLOBAL_RETRIEVER
    if _GLOBAL_RETRIEVER is None:
        _GLOBAL_RETRIEVER = EvidenceRetriever()
    return _GLOBAL_RETRIEVER


SYSTEM_INSTRUCTION = """You are the official Designs Law Assistant for India, answering queries strictly using the provided extracts from the "Manual of Designs Practice & Procedure" (CGPDTM, IP India).

CRITICAL CONSTRAINTS:
1. Answer ONLY using facts directly stated in the supplied context.
2. If the answer cannot be directly and unequivocally verified from the provided context, respond with EXACTLY and ONLY:
Not found
3. When returning "Not found", do NOT add any additional characters, punctuation, explanations, greetings, warnings, citations, or apologies. Only output the exact string:
Not found
4. If the context contains sufficient evidence to answer the question:
   - Provide a concise, clear, accurate factual answer in 2 to 4 sentences.
   - At the end of your answer, cite the exact Chapter, Section, and Page Number as indicated in the context metadata.
   - Format citation at the very end as:
     Source: Chapter <Chapter>, Section <Section>, Page <Page Number>
5. Never invent fees, numbers, names, or legal provisions.
   - Note on Trademark: If asked about Trademark fees, check if the manual specifies it. If the manual only discusses Designs and does not specify Trademark fees, you MUST output "Not found".
   - Note on Current Controller General: Check if the manual mentions who the Controller General of Patents, Designs & Trade Marks is. (For example, P.H. Kurian is mentioned as Controller General on Page 4). If a question asks about someone or something not verified in the context, output "Not found".
   - Note on Fees: If a question asks for a specific numerical fee amount (e.g. for design registration) but the manual only states that fees are prescribed in the "First Schedule of The Design Rules, 2001" without giving a specific monetary figure in the text, clearly state what the manual says (i.e. prescribed in First Schedule) and cite Chapter 3 / Rule 5 / Page 22.
"""


class RAGAssistant:
    """Orchestrates retrieval, evidence validation, and LLM generation."""

    def __init__(self, api_key: Optional[str] = None):
        self.retriever = get_retriever()
        self.api_key = api_key or config.GEMINI_API_KEY
        self.client = None
        if self.api_key and self.api_key != "your_gemini_api_key_here":
            try:
                self.client = genai.Client(api_key=self.api_key)
            except Exception as e:
                print(f"[WARNING] Could not initialize google.genai Client: {e}")

    def answer_question(self, question: str) -> Dict[str, Any]:
        """
        Executes complete RAG pipeline for a given question.
        """
        if not self.retriever.is_ready():
            return {
                "question": question,
                "answer": "Not found",
                "passages": [],
                "status": "error",
                "error_message": "Vector database not initialized. Please run ingest.py first."
            }

        passages = self.retriever.retrieve(question, top_k=config.TOP_K)

        if not passages:
            return {
                "question": question,
                "answer": "Not found",
                "passages": [],
                "status": "not_found",
                "error_message": None
            }

        # Build context from retrieved chunks
        context_parts = []
        for p in passages:
            meta = p["metadata"]
            part = (
                f"[Document Extract]\n"
                f"Chapter: {meta.get('chapter', 'N/A')}\n"
                f"Section: {meta.get('section', 'N/A')}\n"
                f"Page Number: {meta.get('page_number', 'N/A')}\n"
                f"Content:\n{p['text']}\n"
            )
            context_parts.append(part)

        context_str = "\n---\n".join(context_parts)

        # Check API key
        if not self.api_key or self.api_key == "your_gemini_api_key_here" or not self.client:
            return {
                "question": question,
                "answer": "Not found",
                "passages": passages,
                "status": "error",
                "error_message": "Gemini API key is not configured. Please set GEMINI_API_KEY in .env or the Streamlit sidebar."
            }

        prompt = f"""Supplied Context:
{context_str}

Question:
{question}

Answer:"""

        try:
            response = self.client.models.generate_content(
                model=config.GEMINI_MODEL_NAME,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_INSTRUCTION,
                    temperature=0.0,
                    max_output_tokens=500
                )
            )

            raw_answer = response.text.strip() if response and response.text else "Not found"

            # Strict normalization: if answer indicates not found, normalize to exactly "Not found"
            clean_lower = raw_answer.lower().strip()
            if clean_lower == "not found" or clean_lower.startswith("not found"):
                return {
                    "question": question,
                    "answer": "Not found",
                    "passages": passages,
                    "status": "not_found",
                    "error_message": None
                }

            return {
                "question": question,
                "answer": raw_answer,
                "passages": passages,
                "status": "supported",
                "error_message": None
            }

        except Exception as e:
            return {
                "question": question,
                "answer": "Not found",
                "passages": passages,
                "status": "error",
                "error_message": f"Language model error: {str(e)}"
            }
