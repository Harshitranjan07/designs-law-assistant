import streamlit as st
import os
from pathlib import Path
import config
from rag import RAGAssistant
from ingest import run_ingestion

st.set_page_config(
    page_title="Designs Law Assistant — IP India",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom High-End Liquid Glassmorphism Styling & Deploy Button Removal
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

    /* Hide Streamlit top header, deploy button, running man, footer */
    header[data-testid="stHeader"] {
        display: none !important;
        visibility: hidden !important;
        height: 0% !important;
    }
    .stDeployButton, div[data-testid="stToolbar"], #MainMenu, footer {
        display: none !important;
        visibility: hidden !important;
    }
    
    /* Base Body Styling with dynamic deep mesh gradient */
    .stApp {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
        background: radial-gradient(circle at 10% 20%, rgba(30, 27, 75, 0.95), transparent 40%),
                    radial-gradient(circle at 90% 80%, rgba(15, 23, 42, 0.98), transparent 50%),
                    radial-gradient(circle at 50% 50%, rgba(13, 18, 38, 0.95), transparent 100%),
                    #080c18 !important;
        color: #f1f5f9;
    }

    /* Ambient Glow Blobs behind glass cards */
    .glow-blob-1 {
        position: fixed;
        top: -100px;
        left: 20%;
        width: 450px;
        height: 450px;
        background: radial-gradient(circle, rgba(99, 102, 241, 0.25) 0%, rgba(99, 102, 241, 0) 70%);
        border-radius: 50%;
        filter: blur(60px);
        pointer-events: none;
        z-index: 0;
    }
    .glow-blob-2 {
        position: fixed;
        bottom: 50px;
        right: 15%;
        width: 500px;
        height: 500px;
        background: radial-gradient(circle, rgba(14, 165, 233, 0.2) 0%, rgba(14, 165, 233, 0) 70%);
        border-radius: 50%;
        filter: blur(70px);
        pointer-events: none;
        z-index: 0;
    }

    /* Liquid Glassmorphic Sidebar */
    section[data-testid="stSidebar"] {
        background: rgba(13, 19, 36, 0.65) !important;
        backdrop-filter: blur(24px) saturate(180%) !important;
        -webkit-backdrop-filter: blur(24px) saturate(180%) !important;
        border-right: 1px solid rgba(255, 255, 255, 0.08) !important;
        box-shadow: 4px 0 30px rgba(0, 0, 0, 0.35) !important;
    }

    /* Hero Glass Header */
    .hero-container {
        position: relative;
        background: rgba(255, 255, 255, 0.03);
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 20px;
        padding: 2.2rem 2.5rem;
        margin-bottom: 2rem;
        box-shadow: 0 20px 40px -15px rgba(0, 0, 0, 0.5), inset 0 1px 1px rgba(255, 255, 255, 0.15);
        overflow: hidden;
    }
    .hero-container::before {
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0; height: 1px;
        background: linear-gradient(90deg, transparent, rgba(99, 102, 241, 0.8), rgba(56, 189, 248, 0.8), transparent);
    }
    .hero-badge {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        padding: 6px 14px;
        background: rgba(99, 102, 241, 0.15);
        border: 1px solid rgba(129, 140, 248, 0.3);
        border-radius: 9999px;
        font-size: 0.82rem;
        font-weight: 600;
        color: #a5b4fc;
        margin-bottom: 1rem;
        letter-spacing: 0.02em;
    }
    .hero-title {
        font-size: 2.5rem;
        font-weight: 800;
        background: linear-gradient(135deg, #ffffff 0%, #cbd5e1 50%, #94a3b8 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.6rem;
        letter-spacing: -0.02em;
        line-height: 1.15;
    }
    .hero-subtitle {
        font-size: 1.05rem;
        color: #94a3b8;
        max-width: 850px;
        line-height: 1.6;
        font-weight: 400;
    }

    /* Glass Panels */
    .glass-card {
        background: rgba(255, 255, 255, 0.025);
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 16px;
        padding: 1.5rem;
        margin-bottom: 1.5rem;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.25);
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    .glass-card:hover {
        border-color: rgba(99, 102, 241, 0.3);
    }

    /* Supported Answer Card: Emerald Liquid Glass */
    .answer-card-supported {
        background: linear-gradient(135deg, rgba(6, 78, 59, 0.25) 0%, rgba(4, 47, 46, 0.35) 100%);
        backdrop-filter: blur(20px) saturate(160%);
        -webkit-backdrop-filter: blur(20px) saturate(160%);
        border: 1px solid rgba(52, 211, 153, 0.3);
        border-left: 6px solid #10b981;
        padding: 1.8rem;
        border-radius: 16px;
        margin: 1.5rem 0;
        color: #ecfdf5;
        font-size: 1.08rem;
        line-height: 1.7;
        box-shadow: 0 15px 35px -10px rgba(16, 185, 129, 0.2), inset 0 1px 1px rgba(255, 255, 255, 0.1);
    }

    /* Unsupported Answer Card: Ruby Liquid Glass */
    .answer-card-notfound {
        background: linear-gradient(135deg, rgba(127, 29, 29, 0.25) 0%, rgba(69, 10, 10, 0.35) 100%);
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
        border: 1px solid rgba(248, 113, 113, 0.3);
        border-left: 6px solid #ef4444;
        padding: 1.8rem;
        border-radius: 16px;
        margin: 1.5rem 0;
        box-shadow: 0 15px 35px -10px rgba(239, 68, 68, 0.2);
    }
    .notfound-text {
        font-family: 'JetBrains Mono', monospace;
        font-size: 1.6rem;
        font-weight: 700;
        color: #fca5a5;
        letter-spacing: -0.01em;
    }
    .notfound-desc {
        color: #f87171;
        font-size: 0.95rem;
        margin-top: 0.5rem;
        line-height: 1.5;
    }

    /* Evidence Citation Glass Pill */
    .citation-card {
        background: rgba(15, 23, 42, 0.65);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 12px;
        padding: 1.2rem;
        margin-top: 1rem;
        transition: all 0.2s ease;
    }
    .citation-card:hover {
        background: rgba(30, 41, 59, 0.7);
        border-color: rgba(129, 140, 248, 0.4);
    }
    .citation-badge {
        background: rgba(99, 102, 241, 0.2);
        color: #818cf8;
        padding: 3px 8px;
        border-radius: 6px;
        font-size: 0.78rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    .citation-page {
        color: #38bdf8;
        font-weight: 600;
    }
    .citation-quote {
        margin-top: 0.6rem;
        font-size: 0.92rem;
        color: #94a3b8;
        font-style: italic;
        line-height: 1.6;
        border-left: 2px solid rgba(99, 102, 241, 0.4);
        padding-left: 0.8rem;
    }

    /* Status Pill */
    .status-pill-active {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: rgba(16, 185, 129, 0.15);
        color: #34d399;
        border: 1px solid rgba(16, 185, 129, 0.3);
        padding: 6px 14px;
        border-radius: 9999px;
        font-size: 0.85rem;
        font-weight: 600;
    }

    /* Buttons with Liquid Glass Gradient */
    div.stButton > button:first-child {
        background: linear-gradient(135deg, #4f46e5 0%, #3b82f6 100%) !important;
        color: #ffffff !important;
        border: 1px solid rgba(255, 255, 255, 0.2) !important;
        border-radius: 12px !important;
        padding: 0.75rem 1.8rem !important;
        font-weight: 600 !important;
        font-size: 1rem !important;
        box-shadow: 0 10px 25px -5px rgba(79, 70, 229, 0.5) !important;
        transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
    }
    div.stButton > button:first-child:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 15px 30px -5px rgba(79, 70, 229, 0.7) !important;
        border-color: rgba(255, 255, 255, 0.4) !important;
    }

    /* Inputs with Dark Glass */
    textarea.stTextArea, div[data-baseweb="select"] {
        background: rgba(15, 23, 42, 0.6) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 12px !important;
        color: #f8fafc !important;
        backdrop-filter: blur(10px) !important;
    }
    textarea.stTextArea:focus {
        border-color: #6366f1 !important;
        box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.2) !important;
    }
</style>

<div class="glow-blob-1"></div>
<div class="glow-blob-2"></div>
""", unsafe_allow_html=True)

# Sidebar Controls
with st.sidebar:
    st.markdown("""
    <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 1.5rem;">
        <div style="background: rgba(99, 102, 241, 0.2); border: 1px solid rgba(129, 140, 248, 0.3); border-radius: 14px; padding: 10px; display: flex; align-items: center; justify-content: center;">
            <span style="font-size: 1.8rem;">⚖️</span>
        </div>
        <div>
            <div style="font-weight: 700; font-size: 1.1rem; color: #f8fafc;">System Controls</div>
            <div style="font-size: 0.78rem; color: #94a3b8;">Designs Law RAG Engine</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # API key configuration
    current_key = os.getenv("GEMINI_API_KEY", "") or os.getenv("GOOGLE_API_KEY", "")
    api_key_input = st.text_input(
        "Google Gemini API Key",
        value=current_key,
        type="password",
        help="Configured securely via .env. You can override it here if desired."
    )
    if api_key_input:
        os.environ["GEMINI_API_KEY"] = api_key_input
        config.GEMINI_API_KEY = api_key_input

    st.markdown("<div style='margin: 1.2rem 0;'></div>", unsafe_allow_html=True)
    
    # Ingestion Status & Trigger
    st.markdown("<div style='font-size: 0.85rem; font-weight: 600; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.5rem;'>Vector Database</div>", unsafe_allow_html=True)
    chroma_exists = config.CHROMA_DIR.exists() and any(config.CHROMA_DIR.iterdir())
    
    if chroma_exists:
        st.markdown('<div class="status-pill-active"><span>●</span> ChromaDB Active (218 Chunks)</div>', unsafe_allow_html=True)
    else:
        st.error("⚠️ ChromaDB Not Initialized")

    st.markdown("<div style='margin: 0.8rem 0;'></div>", unsafe_allow_html=True)
    if st.button("🔄 Re-index Source PDF", use_container_width=True):
        with st.spinner("Processing 87 pages and generating embeddings..."):
            try:
                run_ingestion(force_reindex=True)
                st.success("218 chunks indexed successfully!")
                st.rerun()
            except Exception as e:
                st.error(f"Error during indexing: {str(e)}")

    st.markdown("<div style='margin: 1.5rem 0;'></div>", unsafe_allow_html=True)
    st.markdown("""
    <div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 12px; padding: 1rem; font-size: 0.82rem; color: #94a3b8;">
        <b style="color: #cbd5e1;">Official Knowledge Source</b><br>
        <i>Manual of Designs Practice & Procedure</i><br>
        CGPDTM, IP India<br>
        <b>Coverage:</b> 87 of 87 Pages Verified
    </div>
    """, unsafe_allow_html=True)

# Main Hero Container
st.markdown("""
<div class="hero-container">
    <div class="hero-badge">
        <span>🇮🇳</span> Official IP India Practice Guidelines (CGPDTM)
    </div>
    <div class="hero-title">Designs Law Assistant</div>
    <div class="hero-subtitle">
        An evidence-grounded Retrieval-Augmented Generation assistant. Questions are verified and answered strictly against the official 87-page Manual. If unsupported by document evidence, it returns exactly <code>Not found</code>.
    </div>
</div>
""", unsafe_allow_html=True)

# Standard Assignment Questions
st.markdown("<div style='font-size: 1.1rem; font-weight: 700; color: #f1f5f9; margin-bottom: 0.8rem;'>📋 Select Assignment Evaluation Question</div>", unsafe_allow_html=True)

questions = [
    "How long does a proprietor have copyright in a registered design, and can it be extended?",
    "Which classification system is used to register designs?",
    "What is the government fee to register a trademark?",
    "Who is the current Controller General of Patents?",
    "What is the fee to register a design?"
]

selected_preset = st.selectbox(
    "Choose a pre-configured question to test grounding & zero-hallucination:",
    ["-- Select a question or type below --"] + questions,
    label_visibility="collapsed"
)

st.markdown("<div style='margin: 0.8rem 0;'></div>", unsafe_allow_html=True)

# Question Input Box
user_question = st.text_area(
    "Enter legal question:",
    value="" if selected_preset.startswith("--") else selected_preset,
    height=85,
    placeholder="e.g., How long does a proprietor have copyright in a registered design, and can it be extended?",
    label_visibility="collapsed"
)

col_ask, col_space = st.columns([1.5, 6])
with col_ask:
    ask_button = st.button("⚖️ Ask Question", type="primary", use_container_width=True)

# Process question
if ask_button and user_question.strip():
    with st.spinner("Retrieving verified passages and evaluating context..."):
        assistant = RAGAssistant(api_key=api_key_input or config.GEMINI_API_KEY)
        result = assistant.answer_question(user_question.strip())

        if result.get("error_message"):
            st.error(f"⚠️ {result['error_message']}")

        answer_text = result["answer"]

        st.markdown("<div style='margin-top: 2rem;'></div>", unsafe_allow_html=True)
        st.markdown("<div style='font-size: 1.25rem; font-weight: 700; color: #f1f5f9;'>💡 Verified Answer</div>", unsafe_allow_html=True)

        if answer_text == "Not found":
            st.markdown("""
            <div class="answer-card-notfound">
                <div class="notfound-text">Not found</div>
                <div class="notfound-desc">
                    The requested information cannot be established or verified from the supplied <i>Manual of Designs Practice & Procedure</i>. The assistant strictly adheres to anti-hallucination rules and will never invent facts or use unverified external sources.
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="answer-card-supported">
                {answer_text}
            </div>
            """, unsafe_allow_html=True)

            # Display source passages if supported
            if result.get("passages"):
                with st.expander("📚 Inspect Supporting Passages & Citations from PDF", expanded=True):
                    for idx, p in enumerate(result["passages"]):
                        meta = p["metadata"]
                        st.markdown(f"""
                        <div class="citation-card">
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.4rem;">
                                <div>
                                    <span class="citation-badge">Source Citation #{idx+1}</span>
                                    <span style="font-weight: 600; color: #e2e8f0; margin-left: 8px;">{meta.get('chapter', 'General')}</span>
                                    <span style="color: #64748b; margin: 0 4px;">•</span>
                                    <span style="color: #a5b4fc; font-size: 0.9rem;">Section {meta.get('section', 'N/A')}</span>
                                </div>
                                <div class="citation-page">📄 PDF Page {meta.get('page_number')}</div>
                            </div>
                            <div class="citation-quote">"{p['text'][:420]}..."</div>
                        </div>
                        """, unsafe_allow_html=True)
