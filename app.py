import streamlit as st
import os
from pathlib import Path
import config
from rag import RAGAssistant
from ingest import run_ingestion

st.set_page_config(
    page_title="Designs Law Assistant",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling for modern clean aesthetics
st.markdown("""
<style>
    .main-title {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1e3a8a;
        margin-bottom: 0.2rem;
    }
    .subtitle {
        font-size: 1rem;
        color: #4b5563;
        margin-bottom: 1.5rem;
    }
    .answer-card-supported {
        background-color: #f0fdf4;
        border-left: 5px solid #16a34a;
        padding: 1.2rem;
        border-radius: 6px;
        margin: 1rem 0;
        color: #14532d;
    }
    .answer-card-notfound {
        background-color: #fef2f2;
        border-left: 5px solid #dc2626;
        padding: 1.2rem;
        border-radius: 6px;
        margin: 1rem 0;
        color: #991b1b;
        font-family: monospace;
        font-size: 1.2rem;
        font-weight: bold;
    }
    .source-box {
        background-color: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 6px;
        padding: 0.8rem;
        margin-top: 0.5rem;
        font-size: 0.9rem;
    }
</style>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.image("https://img.icons8.com/color/96/scales--v1.png", width=64)
    st.title("System Controls")
    
    # API key configuration
    current_key = os.getenv("GEMINI_API_KEY", "") or os.getenv("GOOGLE_API_KEY", "")
    api_key_input = st.text_input(
        "Google Gemini API Key",
        value=current_key,
        type="password",
        help="Obtain a free API key at https://aistudio.google.com/"
    )
    if api_key_input:
        os.environ["GEMINI_API_KEY"] = api_key_input
        config.GEMINI_API_KEY = api_key_input

    st.divider()
    
    # Ingestion Status & Trigger
    st.subheader("Database Status")
    chroma_exists = config.CHROMA_DIR.exists() and any(config.CHROMA_DIR.iterdir())
    
    if chroma_exists:
        st.success("✅ ChromaDB Index Active")
    else:
        st.warning("⚠️ ChromaDB Not Initialized")

    if st.button("🔄 Re-index Source PDF"):
        with st.spinner("Processing 87 pages and generating embeddings..."):
            try:
                run_ingestion(force_reindex=True)
                st.success("Indexing completed successfully!")
                st.rerun()
            except Exception as e:
                st.error(f"Error during indexing: {str(e)}")

    st.markdown("---")
    st.markdown("**Knowledge Source:**\n*Manual of Designs Practice & Procedure*, CGPDTM, IP India (87 Pages)")

# Main Area
st.markdown('<div class="main-title">⚖️ Designs Law Assistant</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Retrieval-Augmented Generation (RAG) assistant answering questions exclusively from the official CGPDTM <i>Manual of Designs Practice & Procedure</i>.</div>', unsafe_allow_html=True)

# Standard Assignment Questions
st.subheader("📋 Pre-configured Assignment Questions")
questions = [
    "How long does a proprietor have copyright in a registered design, and can it be extended?",
    "Which classification system is used to register designs?",
    "What is the government fee to register a trademark?",
    "Who is the current Controller General of Patents?",
    "What is the fee to register a design?"
]

selected_preset = st.selectbox(
    "Select an assignment question to quickly test:",
    ["-- Select a question or type below --"] + questions
)

# Question Input Box
user_question = st.text_area(
    "Enter your legal question:",
    value="" if selected_preset.startswith("--") else selected_preset,
    height=80,
    placeholder="e.g., How long does a proprietor have copyright in a registered design, and can it be extended?"
)

col_ask, col_clear = st.columns([1, 5])
with col_ask:
    ask_button = st.button("🔍 Ask Question", type="primary", use_container_width=True)

# Process question
if ask_button and user_question.strip():
    with st.spinner("Retrieving verified passages and evaluating context..."):
        assistant = RAGAssistant(api_key=api_key_input or config.GEMINI_API_KEY)
        result = assistant.answer_question(user_question.strip())

        if result.get("error_message"):
            st.error(f"⚠️ {result['error_message']}")

        # Display answer
        st.subheader("💡 Answer")
        answer_text = result["answer"]

        if answer_text == "Not found":
            st.markdown(f'<div class="answer-card-notfound">Not found</div>', unsafe_allow_html=True)
            st.info("ℹ️ The requested information is not supported or contained within the provided *Manual of Designs Practice & Procedure* PDF.")
        else:
            st.markdown(f'<div class="answer-card-supported">{answer_text}</div>', unsafe_allow_html=True)

            # Display source passages if supported
            if result.get("passages"):
                with st.expander("📚 Retrieved Supporting Evidence & Citations from PDF", expanded=True):
                    for idx, p in enumerate(result["passages"]):
                        meta = p["metadata"]
                        st.markdown(f"""
                        <div class="source-box">
                            <b>Citation #{idx+1}:</b> Chapter: <i>{meta.get('chapter', 'General')}</i> | Section: <i>{meta.get('section', 'N/A')}</i> | <b>PDF Page {meta.get('page_number')}</b><br>
                            <b>Similarity Score:</b> {p.get('similarity', 0.0):.3f}<br>
                            <div style="margin-top: 5px; color: #374151; font-style: italic;">"{p['text'][:400]}..."</div>
                        </div>
                        """, unsafe_allow_html=True)
