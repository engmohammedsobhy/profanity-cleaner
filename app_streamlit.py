from __future__ import annotations
import os
os.environ["TF_USE_LEGACY_KERAS"] = "1"

import html
import json
import mimetypes
import os
from pathlib import Path
from typing import Any, Dict, List

import detoxifier_page
import stream_toxicity_detection
import streamlit as st
import streamlit.components.v1 as components

import streamlit_workflows as workflows


st.set_page_config(page_title="Profanity Cleaner", layout="wide", page_icon="P")

st.markdown(
    """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=SF+Pro+Display:wght@400;500;600;700&family=Inter:wght@400;500;600;700&display=swap');
        
        :root {
            --bg-black: #000000;
            --card-bg: rgba(28, 28, 30, 0.55);
            --apple-red: #e50914;
            --apple-red-hover: #ff2b36;
            --apple-red-glow: rgba(229, 9, 20, 0.4);
            --apple-red-light: #ff453a;
            --text-primary: #f5f5f7;
            --text-secondary: #86868b;
            --card-radius: 18px;
            --pill-radius: 980px;
        }

        html, body, [class*="css"] {
            font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", "Inter", sans-serif !important;
            -webkit-font-smoothing: antialiased;
        }

        .stApp {
            background-color: #000000 !important;
            background-image: radial-gradient(circle at 50% -10%, #261a1a 0%, #000000 75%) !important;
            color: var(--text-primary) !important;
        }

        /* Unified Spacing and Compact Gaps */
        [data-testid="stVerticalBlock"] > div {
            gap: 0.75rem !important;
        }
        
        div[data-testid="stForm"], div.stContainer > div {
            background: var(--card-bg) !important;
            backdrop-filter: blur(30px) !important;
            -webkit-backdrop-filter: blur(30px) !important;
            border: none !important;
            border-radius: var(--card-radius) !important;
            padding: 1.1rem 1.25rem !important;
            box-shadow: 0 4px 24px 0 rgba(0, 0, 0, 0.25) !important;
        }

        [data-testid="stSidebar"] {
            background: rgba(12, 10, 10, 0.85) !important;
            backdrop-filter: blur(35px) !important;
            -webkit-backdrop-filter: blur(35px) !important;
            border-right: 1px solid rgba(255, 255, 255, 0.08) !important;
        }

        .apple-title {
            font-size: 2.5rem;
            font-weight: 700;
            color: #ffffff;
            letter-spacing: -0.03em;
            margin-bottom: 0.2rem;
            line-height: 1.1;
        }

        .apple-subtitle {
            color: var(--text-secondary);
            font-size: 1.05rem;
            font-weight: 400;
            letter-spacing: -0.01em;
            margin-bottom: 1rem;
        }

        .section-label {
            font-size: 0.78rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            color: var(--text-secondary);
            margin-bottom: 0.5rem;
        }

        /* Expander Collapsible Styling */
        div[data-testid="stExpander"] {
            background: rgba(22, 18, 18, 0.6) !important;
            border: none !important;
            border-radius: 14px !important;
            margin-top: 0.6rem !important;
            margin-bottom: 0.6rem !important;
        }

        div[data-testid="stExpander"] summary {
            font-weight: 600 !important;
            font-size: 0.9rem !important;
            color: #f5f5f7 !important;
        }

        div[data-testid="stExpander"] summary:hover {
            color: var(--apple-red-light) !important;
        }

        /* Home Page Sleek Feature Cards */
        .home-card {
            background: rgba(28, 28, 30, 0.65) !important;
            border: 1px solid rgba(255, 255, 255, 0.08) !important;
            border-radius: 20px !important;
            padding: 1.4rem 1.6rem !important;
            backdrop-filter: blur(30px) !important;
            -webkit-backdrop-filter: blur(30px) !important;
            transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1) !important;
            min-height: 220px;
        }

        .home-card:hover {
            border-color: rgba(229, 9, 20, 0.4) !important;
            box-shadow: 0 10px 30px rgba(229, 9, 20, 0.15) !important;
            transform: translateY(-2px) !important;
        }

        .home-badge {
            display: inline-block;
            background: linear-gradient(135deg, rgba(229, 9, 20, 0.25), rgba(255, 69, 58, 0.15));
            border: 1px solid rgba(229, 9, 20, 0.4);
            color: #ff453a;
            font-size: 0.72rem;
            font-weight: 700;
            letter-spacing: 0.08em;
            padding: 0.25rem 0.75rem;
            border-radius: var(--pill-radius);
            margin-bottom: 0.75rem;
            text-transform: uppercase;
        }

        .home-card-title {
            font-size: 1.35rem;
            font-weight: 700;
            color: #ffffff;
            margin-bottom: 0.4rem;
            letter-spacing: -0.02em;
        }

        .home-card-desc {
            color: var(--text-secondary);
            font-size: 0.92rem;
            line-height: 1.45;
            margin-bottom: 0.9rem;
        }

        .home-feature-item {
            color: #e5e5ea;
            font-size: 0.86rem;
            margin-bottom: 0.4rem;
            line-height: 1.4;
        }

        /* Apple Metric Strips */
        .metric-card {
            background: rgba(255, 255, 255, 0.03);
            backdrop-filter: blur(20px);
            border: none;
            padding: 1.1rem 1.3rem;
            border-radius: 16px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
            transition: transform 0.2s ease;
        }

        .metric-card:hover {
            transform: translateY(-2px);
        }

        .metric-label {
            color: var(--text-secondary);
            font-size: 0.73rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.08em;
        }

        .metric-value {
            font-size: 1.8rem;
            font-weight: 700;
            color: var(--text-primary);
            margin-top: 0.2rem;
            letter-spacing: -0.03em;
        }

        /* Apple Red Pill Buttons */
        .stButton > button {
            border-radius: var(--pill-radius) !important;
            font-weight: 600 !important;
            font-size: 0.95rem !important;
            padding: 0.65rem 1.5rem !important;
            transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1) !important;
            border: none !important;
            background: var(--apple-red) !important;
            color: #ffffff !important;
            letter-spacing: -0.01em !important;
            box-shadow: 0 4px 16px var(--apple-red-glow) !important;
        }

        .stButton > button:hover {
            background: var(--apple-red-hover) !important;
            color: #ffffff !important;
            box-shadow: 0 6px 22px rgba(229, 9, 20, 0.55) !important;
            transform: scale(1.015) !important;
        }

        .stButton > button:active {
            transform: scale(0.98) !important;
        }

        .stButton > button:disabled {
            background: rgba(255, 255, 255, 0.08) !important;
            color: var(--text-secondary) !important;
            border-color: transparent !important;
            box-shadow: none !important;
        }

        .stButton > button[kind="secondary"] {
            background: rgba(255, 255, 255, 0.07) !important;
            color: var(--text-primary) !important;
            border: none !important;
            box-shadow: none !important;
        }

        .stButton > button[kind="secondary"]:hover {
            background: rgba(255, 255, 255, 0.14) !important;
            color: #ffffff !important;
        }

        /* Secondary Download Buttons */
        .stDownloadButton > button {
            border-radius: var(--pill-radius) !important;
            font-weight: 600 !important;
            border: none !important;
            background: rgba(255, 255, 255, 0.07) !important;
            color: var(--text-primary) !important;
            transition: all 0.2s ease !important;
        }

        .stDownloadButton > button:hover {
            background: rgba(229, 9, 20, 0.18) !important;
            color: #ffffff !important;
            box-shadow: 0 4px 14px var(--apple-red-glow) !important;
        }

        textarea, input, select, div[data-baseweb="select"] > div {
            border-radius: 12px !important;
            background: rgba(0, 0, 0, 0.45) !important;
            border: 1px solid rgba(255, 255, 255, 0.1) !important;
            color: var(--text-primary) !important;
            font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Inter", sans-serif !important;
            transition: border-color 0.2s ease, box-shadow 0.2s ease !important;
        }

        textarea:focus, input:focus, select:focus, div[data-baseweb="select"]:focus-within {
            border-color: var(--apple-red) !important;
            box-shadow: 0 0 0 3px var(--apple-red-glow) !important;
            outline: none !important;
        }

        textarea::placeholder, input::placeholder {
            color: #6e6e73 !important;
        }

        /* High Contrast Streamlit Red Accent Overrides */
        [data-baseweb="slider"] div[role="slider"] {
            background-color: var(--apple-red) !important;
            border: 2px solid #ffffff !important;
        }

        [data-baseweb="slider"] div[data-testid="stSliderTickBar"] + div {
            background-color: var(--apple-red) !important;
        }

        div[data-baseweb="checkbox"] input:checked + div {
            background-color: var(--apple-red) !important;
            border-color: var(--apple-red) !important;
        }

        div[data-baseweb="radio"] input:checked + div {
            border-color: var(--apple-red) !important;
        }

        div[data-baseweb="radio"] input:checked + div > div {
            background-color: var(--apple-red) !important;
        }

        button[data-baseweb="tab"] {
            border-radius: var(--pill-radius) !important;
            font-weight: 500 !important;
            color: var(--text-secondary) !important;
            padding: 0.4rem 1.1rem !important;
        }

        button[data-baseweb="tab"][aria-selected="true"] {
            color: #ffffff !important;
            background: rgba(229, 9, 20, 0.2) !important;
        }

        div[data-baseweb="tab-highlight"] {
            background-color: var(--apple-red) !important;
        }

        div[data-testid="stProgress"] > div > div > div {
            background-color: var(--apple-red) !important;
            background-image: linear-gradient(90deg, #e50914, #ff453a) !important;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


def init_state() -> None:
    defaults = {
        "media_result": None,
        "text_result": None,
        "media_logs": [],
        "text_logs": [],
        "current_page": "Home",
        "active_media_key": None,
        "active_text_val": "",
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


class StreamlitStatus:
    def __init__(self, progress_slot: Any, state_key: str):
        self.progress_slot = progress_slot
        self.state_key = state_key
        st.session_state[self.state_key] = []

    def emit(self, message: Any) -> None:
        if isinstance(message, (int, float)):
            value = max(0, min(100, int(message)))
            self.progress_slot.progress(value / 100)
            return
        text = str(message)
        st.session_state[self.state_key].append(text)


def file_bytes(path: str) -> bytes:
    with open(path, "rb") as handle:
        return handle.read()


def download_path(path: str, label: str) -> None:
    if not path or not os.path.exists(path):
        return
    mime, _ = mimetypes.guess_type(path)
    st.download_button(label, file_bytes(path), file_name=os.path.basename(path), mime=mime or "application/octet-stream", use_container_width=True)


def render_copy_button(text: str) -> None:
    payload = json.dumps(text)
    components.html(
        f"""
        <button onclick='navigator.clipboard.writeText({payload})'
                style='border:none;background:rgba(255,255,255,0.08);color:#f5f5f7;border-radius:980px;padding:9px 14px;font-weight:600;cursor:pointer;width:100%;font-family:-apple-system,BlinkMacSystemFont,sans-serif;font-size:0.85rem;'>
            Copy Cleaned Text
        </button>
        """,
        height=44,
    )


def render_mascot(state: str) -> None:
    pass


def compact_rows(rows: List[Dict[str, Any]], keys: List[str]) -> List[Dict[str, Any]]:
    return [{key: row.get(key) for key in keys} for row in rows]


def render_header() -> None:
    st.markdown("<div class='apple-title'>Profanity Cleaner</div>", unsafe_allow_html=True)
    st.markdown("<div class='apple-subtitle'>Intelligent media moderation, speech censoring, toxicity detection & AI detoxification.</div>", unsafe_allow_html=True)


def render_home_page() -> None:
    st.markdown(
        """
        <div style="background: linear-gradient(135deg, rgba(229, 9, 20, 0.15) 0%, rgba(28, 28, 30, 0.65) 100%); 
                    border: 1px solid rgba(229, 9, 20, 0.3); 
                    border-radius: 20px; 
                    padding: 1.6rem 2rem; 
                    margin-bottom: 1.2rem; 
                    backdrop-filter: blur(25px);
                    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);">
            <div class="home-badge">Content Moderation Engine v2.0</div>
            <h2 style="color: #ffffff; font-size: 1.85rem; font-weight: 700; margin: 0.2rem 0 0.5rem 0; letter-spacing: -0.02em;">
                Next-Gen Moderation & Generative AI Detoxification
            </h2>
            <p style="color: #a1a1a6; font-size: 1.02rem; margin: 0; line-height: 1.5;">
                Unified suite for neural toxicity classification, automated polite rephrasing, audio/video speech censoring, and granular linguistic analysis.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns(2, gap="medium")

    with col1:
        st.markdown(
            """
            <div class="home-card">
                <div class="home-badge">Deep Learning AI</div>
                <div class="home-card-title">Toxicity Detection</div>
                <div class="home-card-desc">
                    Multi-label neural network classification quantifying toxicity across 6 risk dimensions with real-time score breakdown.
                </div>
                <div class="home-feature-item"><b>6 Categories</b>: Toxic, Severe Toxic, Obscene, Threat, Insult, Identity Hate.</div>
                <div class="home-feature-item"><b>Sensitivity Slider</b>: Custom probability threshold filtering.</div>
                <div class="home-feature-item"><b>Multi-Modal Input</b>: Text and Media Transcription.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("<div style='height:4px;'></div>", unsafe_allow_html=True)
        st.button(
            "Launch Toxicity Detection",
            key="home_btn_tox",
            use_container_width=True,
            type="primary",
            on_click=set_page,
            args=("Toxicity Detection",),
        )

        st.markdown("<div style='height:14px;'></div>", unsafe_allow_html=True)

        st.markdown(
            """
            <div class="home-card">
                <div class="home-badge">Speech & Audio Engine</div>
                <div class="home-card-title">Media Moderation</div>
                <div class="home-card-desc">
                    Frame-accurate audio bleeping, timestamped speech muting, and automated subtitle export for videos and recordings.
                </div>
                <div class="home-feature-item"><b>Whisper ASR</b>: High-precision speech-to-text transcription.</div>
                <div class="home-feature-item"><b>Censor Audio</b>: Mute audio intervals or overlay custom bleep sound.</div>
                <div class="home-feature-item"><b>Export Subtitles</b>: Generate raw & clean .SRT & JSON logs.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("<div style='height:4px;'></div>", unsafe_allow_html=True)
        st.button(
            "Launch Media Moderation",
            key="home_btn_media",
            use_container_width=True,
            type="primary",
            on_click=set_page,
            args=("Media Moderation",),
        )

    with col2:
        st.markdown(
            """
            <div class="home-card">
                <div class="home-badge">LLM Generative AI</div>
                <div class="home-card-title">Toxicity Detoxifier</div>
                <div class="home-card-desc">
                    Intelligent text rephrasing engine that automatically converts toxic or aggressive text into polite, professional communication.
                </div>
                <div class="home-feature-item"><b>Context Rewriting</b>: Preserves sentence meaning without hostility.</div>
                <div class="home-feature-item"><b>Diff Highlighting</b>: Visual side-by-side comparison.</div>
                <div class="home-feature-item"><b>Smart Bypassing</b>: Leaves non-toxic text completely untouched.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("<div style='height:4px;'></div>", unsafe_allow_html=True)
        st.button(
            "Launch Toxicity Detoxifier",
            key="home_btn_detox",
            use_container_width=True,
            type="primary",
            on_click=set_page,
            args=("Toxicity Detoxifier",),
        )

        st.markdown("<div style='height:14px;'></div>", unsafe_allow_html=True)

        st.markdown(
            """
            <div class="home-card">
                <div class="home-badge">Linguistics & Dictionary</div>
                <div class="home-card-title">Text NLP Moderation</div>
                <div class="home-card-desc">
                    Rule-based text sanitization with obfuscation detection (leet speak, unicode tricks) and custom word override lists.
                </div>
                <div class="home-feature-item"><b>Obfuscation Removal</b>: Unmasks hidden profanity patterns.</div>
                <div class="home-feature-item"><b>Category Rules</b>: 13 granular profanity classes.</div>
                <div class="home-feature-item"><b>Linguistic Metrics</b>: POS tagging & profanity density analysis.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("<div style='height:4px;'></div>", unsafe_allow_html=True)
        st.button(
            "Launch Text NLP",
            key="home_btn_nlp",
            use_container_width=True,
            type="primary",
            on_click=set_page,
            args=("Text NLP",),
        )

    st.markdown("<div style='height:20px;'></div>", unsafe_allow_html=True)
    st.markdown(
        """
        <div style="text-align: center; border-top: 1px solid rgba(255,255,255,0.08); padding-top: 1rem; color: #86868b; font-size: 0.82rem;">
            <span>Powered by <b>TensorFlow 2.15 (Bi-LSTM)</b> • <b>OpenAI Whisper ASR</b> • <b>Generative LLM</b> • <b>Streamlit Cloud Engine</b></span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_metric_grid(stats: Dict[str, Any], mapping: List[tuple[str, str]]) -> None:
    cols = st.columns(len(mapping))
    for col, (label, key) in zip(cols, mapping):
        with col:
            st.markdown(
                f"""
                <div class='metric-card'>
                    <div class='metric-label'>{html.escape(label)}</div>
                    <div class='metric-value'>{stats.get(key, 0)}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def render_media_result(result: Dict[str, Any]) -> None:
    if not result:
        return
    st.markdown("<div class='section-label'>Summary</div>", unsafe_allow_html=True)
    render_metric_grid(
        result.get("summary", {}),
        [
            ("Total Words", "word_count"),
            ("Profanity Hits", "profane_word_count"),
            ("Flagged Segments", "flagged_count"),
        ],
    )
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(result.get("summary_html", ""), unsafe_allow_html=True)

    censored_path = result.get("censored_path", "")

    st.markdown("<div class='section-label'>Downloads</div>", unsafe_allow_html=True)
    downloads = st.columns(3)
    with downloads[0]:
        download_path(censored_path, "Download Censored Media")
    with downloads[1]:
        download_path(result.get("log_path", ""), "Download JSON Log")
    with downloads[2]:
        if result.get("transcript_paths"):
            for name, path in result["transcript_paths"].items():
                download_path(path, f"Download {name.replace('_', ' ').title()}")

    st.markdown("<br>", unsafe_allow_html=True)
    prev_col, logs_col = st.columns([2, 4], gap="medium")
    is_video = False
    with prev_col:
        st.markdown("<div class='section-label'>Censored Media Preview</div>", unsafe_allow_html=True)
        if censored_path and os.path.exists(censored_path):
            ext = Path(censored_path).suffix.lower()
            if ext in [".mp4", ".mkv", ".avi", ".mov", ".webm"]:
                _p1, v_box, _p2 = st.columns([0.05, 0.9, 0.05])
                with v_box:
                    st.video(censored_path)
                is_video = True
            else:
                st.audio(censored_path)
        else:
            st.info("Preview unavailable.")

    with logs_col:
        st.markdown("<div class='section-label'>Word Logs</div>", unsafe_allow_html=True)
        flagged = [row for row in result.get("log", []) if row.get("is_profane")]
        table_rows = flagged or result.get("log", [])[:250]
        if table_rows:
            formatted_logs = []
            for row in table_rows:
                s_ms = int(row.get("start_ms", 0) or 0)
                e_ms = int(row.get("end_ms", 0) or 0)
                formatted_logs.append(
                    {
                        "Start Time": f"{s_ms // 60000:02d}:{(s_ms % 60000) / 1000:05.2f}",
                        "End Time": f"{e_ms // 60000:02d}:{(e_ms % 60000) / 1000:05.2f}",
                        "Word": str(row.get("word", "")).strip(),
                        "Profane": bool(row.get("is_profane", False)),
                    }
                )
            calc_height = min(600, max(420 if is_video else 220, len(table_rows) * 36 + 40))
            st.dataframe(
                formatted_logs,
                column_config={
                    "Start Time": st.column_config.TextColumn("Start Time", width="small", help="Start timestamp (MM:SS.ms)"),
                    "End Time": st.column_config.TextColumn("End Time", width="small", help="End timestamp (MM:SS.ms)"),
                    "Word": st.column_config.TextColumn("Word", width="medium"),
                    "Profane": st.column_config.CheckboxColumn("Profane", width="small"),
                },
                use_container_width=True,
                hide_index=True,
                height=calc_height,
            )


def render_category_selector(key_prefix: str) -> List[str]:
    st.markdown("<div class='section-label'>Word Categories to Censor</div>", unsafe_allow_html=True)
    cat_keys = list(workflows.WORD_CATEGORIES.keys())
    cols = st.columns(4)
    selected = []
    for idx, cat_name in enumerate(cat_keys):
        col = cols[idx % 4]
        with col:
            is_checked = st.checkbox(
                cat_name,
                value=True,
                key=f"{key_prefix}_cat_{idx}",
                help=f"Words included in {cat_name}: {', '.join(list(workflows.WORD_CATEGORIES[cat_name])[:4])}...",
            )
            if is_checked:
                selected.append(cat_name)
    return selected


def render_media_tab() -> None:
    # Set left to right column ratio 2:4 (1/3 left, 2/3 right)
    input_col, options_col = st.columns([2, 4], gap="medium")

    with input_col:
        with st.container():
            uploaded_media = st.file_uploader(
                "Input Media File",
                type=[ext.strip(".") for ext in workflows.MEDIA_EXTENSIONS],
                key="media_upload",
                label_visibility="collapsed",
                help="Upload any video (.mp4, .mkv, .mov, .avi) or audio file (.mp3, .wav, .m4a).",
            )

            if uploaded_media:
                media_key = f"{uploaded_media.name}_{uploaded_media.size}"
                if st.session_state.get("active_media_key") != media_key:
                    st.session_state.media_result = None
                    st.session_state.active_media_key = media_key

                suffix = Path(uploaded_media.name).suffix.lower()
                # Compact video preview player
                _left_pad, video_box, _right_pad = st.columns([0.05, 0.9, 0.05])
                with video_box:
                    if suffix in (".mp4", ".mkv", ".avi", ".mov", ".webm"):
                        st.video(uploaded_media)
                    else:
                        st.audio(uploaded_media)

                st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
                process = st.button("Start Media Processing", type="primary", use_container_width=True)
            else:
                st.session_state.media_result = None
                st.session_state.active_media_key = None
                process = False

            render_mascot("media")

    with options_col:
        # Tabbed Option Panel for clean feature navigation
        tab_mod, tab_audio, tab_export = st.tabs([
            "Moderation & Rules",
            "Audio & Censoring",
            "Exports & Output",
        ])

        with tab_mod:
            c1, _c2 = st.columns([0.5, 0.5])
            with c1:
                asr_label = st.selectbox(
                    "ASR Model (Whisper)",
                    list(workflows.ASR_MODELS.keys()),
                    index=1,
                    help="Whisper speech recognition model size. Larger models provide higher transcription accuracy.",
                )

            media_selected_categories = render_category_selector("media")

            st.markdown("<div style='height:6px;'></div>", unsafe_allow_html=True)
            wl_col, bl_col = st.columns(2)
            with wl_col:
                selected_whitelist = st.text_area(
                    "Whitelist",
                    placeholder="Allowed words (e.g. god, damn)",
                    height=110,
                    key="media_whitelist",
                    help="Words listed here will NEVER be censored, overriding standard profanity filters.",
                )
            with bl_col:
                selected_blacklist = st.text_area(
                    "Blacklist",
                    placeholder="Forced censor words (e.g. idiot)",
                    height=110,
                    key="media_blacklist",
                    help="Words listed here will ALWAYS be censored, even if not in standard profanity dictionary.",
                )

        with tab_audio:
            censor_style_choice = st.radio(
                "Censoring Style",
                options=["Silence", "One sound", "Multiple sounds"],
                index=1,
                horizontal=True,
                help="Choose whether to mute flagged words silently, play a single censor bleep, or layer multiple sounds.",
            )

            mode_map = {"Silence": "silence", "One sound": "sound", "Multiple sounds": "multiple_sounds"}
            mode = mode_map[censor_style_choice]
            sound_map = {"Sine wave": "B", "Quack": "Q", "Dolphin": "D", "Triggered": "T", "Custom": "C"}

            sound_choice_keys = []
            custom_sound_path = ""
            custom_sound_paths = []

            if mode == "sound":
                selected_sound = st.selectbox("Sound Choice", list(sound_map.keys()), help="Select the audio bleep/effect to play during profane words.")
                sound_choice_keys = [sound_map[selected_sound]]
                if selected_sound == "Custom":
                    uploaded_custom_sound = st.file_uploader("Upload Custom Audio (WAV/MP3)", type=["wav", "mp3", "ogg"], accept_multiple_files=True, key="custom_sound")
                    if uploaded_custom_sound:
                        custom_sound_paths = workflows.save_uploaded_files(uploaded_custom_sound, "profanity_cleaner_custom")
                        custom_sound_path = custom_sound_paths[0] if custom_sound_paths else ""

            elif mode == "multiple_sounds":
                selected_sounds = st.multiselect(
                    "Sound Choices",
                    options=list(sound_map.keys()),
                    default=["Sine wave", "Quack", "Dolphin"],
                    help="Selected sounds will be overlaid together at each profane word timestamp.",
                )
                sound_choice_keys = [sound_map[s] for s in selected_sounds]
                if "Custom" in selected_sounds:
                    uploaded_custom_sounds = st.file_uploader("Upload Custom Audio Files (WAV/MP3)", type=["wav", "mp3", "ogg"], accept_multiple_files=True, key="custom_sound_multi")
                    if uploaded_custom_sounds:
                        custom_sound_paths = workflows.save_uploaded_files(uploaded_custom_sounds, "profanity_cleaner_custom")
                        custom_sound_path = custom_sound_paths[0] if custom_sound_paths else ""

            st.markdown("<div style='height:6px;'></div>", unsafe_allow_html=True)
            with st.expander("Advanced Audio & Timing Controls", expanded=False):
                overlap_censor = False
                marked_audio_volume = 100.0

                if mode in ["sound", "multiple_sounds"]:
                    c1, c2 = st.columns(2)
                    with c1:
                        overlap_censor = st.checkbox("Overlap censor audio", value=False, help="Keep original audio audible underneath the censor sound instead of completely muting it.")
                    with c2:
                        marked_audio_volume = st.slider(
                            "Original Audio Volume (%)",
                            min_value=0,
                            max_value=100,
                            value=100,
                            step=1,
                            disabled=not overlap_censor,
                            help="Original audio volume level (0-100%) when censor sound plays in overlap mode.",
                        )

                    censor_volume = st.slider("Censor Sound Volume (dB)", min_value=-30.0, max_value=30.0, value=0.0, step=1.0, help="Adjust gain boost or attenuation for censor audio.")
                    loop_censor_sound = st.checkbox("Loop censor sound", value=True, help="Repeats short censor sound continuously until the profane word finishes speaking.")
                else:
                    censor_volume = 0.0
                    loop_censor_sound = True

                use_padding = st.checkbox("Time padding", value=True, help="Extend censoring timeframe slightly before and after each flagged word to prevent leaking fast speech syllables.")
                padding_before_sec = 0.05
                padding_after_sec = 0.05
                if use_padding:
                    pad_c1, pad_c2 = st.columns(2)
                    with pad_c1:
                        padding_before_sec = st.number_input("Padding Before (sec)", min_value=0.00, max_value=2.00, value=0.05, step=0.01, format="%.2f", help="Time added before word start timestamp.")
                    with pad_c2:
                        padding_after_sec = st.number_input("Padding After (sec)", min_value=0.00, max_value=2.00, value=0.05, step=0.01, format="%.2f", help="Time added after word end timestamp.")

        with tab_export:
            st.markdown("<div class='section-label'>Transcript & Subtitle Exports</div>", unsafe_allow_html=True)
            export_raw_txt = st.checkbox("Raw .txt (Original transcription)", value=False)
            export_clean_txt = st.checkbox("Clean .txt (Profanity-masked text)", value=False)
            export_raw_srt = st.checkbox("Raw .srt (Original subtitles)", value=False)
            export_clean_srt = st.checkbox("Clean .srt (Profanity-masked subtitles)", value=False)
            export_json = st.checkbox("Log .json (Word-level timestamps)", value=True)

    if process and uploaded_media:
        progress_slot = st.progress(0)
        status = StreamlitStatus(progress_slot, "media_logs")
        try:
            file_path = workflows.save_uploaded_file(uploaded_media, "profanity_cleaner_media")
            options = {
                "selected_categories": media_selected_categories,
                "rating_preset": "Default",
                "asr_model": workflows.ASR_MODELS[asr_label],
                "mode": mode,
                "sound": sound_choice_keys if mode == "multiple_sounds" else (sound_choice_keys[0] if sound_choice_keys else "B"),
                "custom_sound_path": custom_sound_path,
                "custom_sound_paths": custom_sound_paths,
                "censor_volume": censor_volume,
                "loop_censor_sound": loop_censor_sound,
                "overlap_censor": overlap_censor,
                "marked_audio_volume": marked_audio_volume,
                "padding_before_ms": int(padding_before_sec * 1000) if use_padding else 0,
                "padding_after_ms": int(padding_after_sec * 1000) if use_padding else 0,
                "export_raw_txt": export_raw_txt,
                "export_clean_txt": export_clean_txt,
                "export_raw_srt": export_raw_srt,
                "export_clean_srt": export_clean_srt,
                "export_json_log": export_json,
                "whitelist_text": selected_whitelist,
                "blacklist_text": selected_blacklist,
            }
            with st.spinner("Processing media..."):
                st.session_state.media_result = workflows.process_media_file(file_path, options, status, status)
            st.success("Media processing complete.")
        except Exception as exc:
            st.session_state.media_result = None
            st.error(str(exc))

    if st.session_state.media_result:
        with st.container():
            render_media_result(st.session_state.media_result)


def render_text_result(result: Dict[str, Any]) -> None:
    if not result:
        return
    st.markdown("<div class='section-label'>Summary & NLP Metrics</div>", unsafe_allow_html=True)
    stats = result.get("stats", {})
    render_metric_grid(
        stats,
        [
            ("Total Words", "word_count"),
            ("Profanity Hits", "profane_word_count"),
            ("Cleanliness Score", "cleanliness_score"),
            ("Profanity Density", "profanity_density"),
            ("Est. Read Time", "read_time"),
        ],
    )
    st.markdown("<br>", unsafe_allow_html=True)

    # Multi-view output display
    view_tab1, view_tab2, view_tab3 = st.tabs(["Cleaned Output", "Highlighted Flagged View", "Side-by-Side Comparison"])

    with view_tab1:
        result_cols = st.columns([0.7, 0.3])
        with result_cols[0]:
            st.text_area("Cleaned Output Text", value=result.get("cleaned_text", ""), height=220, label_visibility="collapsed")
        with result_cols[1]:
            render_copy_button(result.get("cleaned_text", ""))
            st.markdown("<div style='height:6px;'></div>", unsafe_allow_html=True)
            st.download_button("Download Cleaned Text", result.get("cleaned_text", "").encode("utf-8"), file_name="profanity_cleaned_text.txt", mime="text/plain", use_container_width=True)
            st.download_button(
                "Download NLP JSON",
                json.dumps(result, indent=2, ensure_ascii=False).encode("utf-8"),
                file_name="profanity_text_analysis.json",
                mime="application/json",
                use_container_width=True,
            )
            if result.get("output_path"):
                download_path(result["output_path"], "Download Saved File")

    with view_tab2:
        st.markdown("<div class='section-label'>Visual Profanity Context (Flagged words highlighted in red)</div>", unsafe_allow_html=True)
        html_content = result.get("highlighted_html", "")
        st.markdown(
            f"""
            <div style="background: rgba(10, 10, 12, 0.95); padding: 1.25rem; border-radius: 14px; border: 1px solid rgba(255, 255, 255, 0.08); font-size: 1.05rem; line-height: 1.7; color: #f5f5f7;">
                {html_content}
            </div>
            """,
            unsafe_allow_html=True,
        )

    with view_tab3:
        cmp_col1, cmp_col2 = st.columns(2)
        with cmp_col1:
            st.markdown("<div class='section-label'>Original Raw Text</div>", unsafe_allow_html=True)
            st.text_area("Original Text", value=result.get("raw_text", ""), height=220, label_visibility="collapsed")
        with cmp_col2:
            st.markdown("<div class='section-label'>Cleaned Output Text</div>", unsafe_allow_html=True)
            st.text_area("Cleaned Text", value=result.get("cleaned_text", ""), height=220, label_visibility="collapsed")

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("<div class='section-label'>Detailed Linguistic Analysis</div>", unsafe_allow_html=True)
    token_tab, flagged_tab, sent_tab, vocab_tab = st.tabs(["Word Tokens", "Flagged Tokens", "Sentences", "Vocabulary Stats"])
    with token_tab:
        token_keys = ["index", "text", "normalized", "lemma", "pos_guess", "severity_category", "token_type", "start", "end", "is_stopword", "detection_source"]
        st.dataframe(compact_rows(result.get("word_tokens", []), token_keys), use_container_width=True, hide_index=True)
    with flagged_tab:
        flagged = result.get("flagged_tokens", [])
        if flagged:
            st.dataframe(compact_rows(flagged, ["text", "normalized", "lemma", "pos_guess", "severity_category", "is_obfuscated", "is_blacklisted", "detection_source", "replacement"]), use_container_width=True, hide_index=True)
        else:
            st.info("No flagged tokens detected.")
    with sent_tab:
        st.dataframe(compact_rows(result.get("sentences", []), ["index", "text", "word_count", "replacement"]), use_container_width=True, hide_index=True)
    with vocab_tab:
        top_terms = [{"term": term, "count": count} for term, count in stats.get("top_terms", [])]
        pos_counts = [{"pos": pos, "count": count} for pos, count in stats.get("pos_counts", {}).items()]
        left, right = st.columns(2)
        with left:
            st.markdown("<div class='section-label'>Top Frequent Terms</div>", unsafe_allow_html=True)
            st.dataframe(top_terms, use_container_width=True, hide_index=True)
        with right:
            st.markdown("<div class='section-label'>POS Tag Distribution</div>", unsafe_allow_html=True)
            st.dataframe(pos_counts, use_container_width=True, hide_index=True)


def render_text_tab() -> None:
    # Set left to right column ratio 2:4 (1/3 left, 2/3 right)
    input_col, options_col = st.columns([2, 4], gap="medium")
    
    with input_col:
        with st.container():
            all_exts = [ext.strip(".") for ext in workflows.TEXT_EXTENSIONS + workflows.MEDIA_EXTENSIONS]
            uploaded_file = st.file_uploader(
                "Upload Text, Audio, or Video File",
                type=all_exts,
                key="text_page_upload",
                label_visibility="collapsed",
                help="Upload a text file (.txt, .docx) OR an audio/video file (.mp4, .mp3, .wav, .m4a, .mov, etc.) to transcribe into text.",
            )
            uploaded_path = ""
            loaded_text = ""
            if uploaded_file:
                uploaded_path = workflows.save_uploaded_file(uploaded_file, "profanity_cleaner_text_input")
                ext = Path(uploaded_file.name).suffix.lower()
                if ext in workflows.MEDIA_EXTENSIONS:
                    _p1, media_box, _p2 = st.columns([0.05, 0.9, 0.05])
                    with media_box:
                        if ext in workflows.VIDEO_EXTENSIONS:
                            st.video(uploaded_file)
                        else:
                            st.audio(uploaded_file)
                    
                    asr_label = st.selectbox(
                        "Whisper ASR Model",
                        list(workflows.ASR_MODELS.keys()),
                        index=1,
                        key="text_page_asr_model",
                        help="Select Whisper model size for speech-to-text transcription.",
                    )

                    if st.button("Transcribe Speech to Text", type="secondary", use_container_width=True):
                        progress_slot = st.progress(0)
                        status = StreamlitStatus(progress_slot, "transcribe_text_logs")
                        try:
                            with st.spinner("Transcribing media speech to text..."):
                                extracted = workflows.transcribe_media_to_text(
                                    uploaded_path,
                                    asr_model=workflows.ASR_MODELS[asr_label],
                                    progress_callback=status,
                                )
                            if extracted:
                                st.session_state["active_text_val"] = extracted
                                st.success("Media speech transcribed to text!")
                            else:
                                st.warning("No spoken text detected in media file.")
                        except Exception as exc:
                            st.error(f"Transcription failed: {exc}")
                else:
                    loaded_text = workflows.read_text_file(uploaded_path)
                    if loaded_text and st.session_state.get("last_uploaded_text_path") != uploaded_path:
                        st.session_state["active_text_val"] = loaded_text
                        st.session_state["last_uploaded_text_path"] = uploaded_path

            st.markdown("<div class='section-label'>Sample Presets</div>", unsafe_allow_html=True)
            sp_c1, sp_c2, sp_c3 = st.columns(3)
            with sp_c1:
                if st.button("Sample: Mild", use_container_width=True, type="secondary"):
                    st.session_state["active_text_val"] = "Damn, this is crazy! What the hell is going on here? That idiot lost the game."
            with sp_c2:
                if st.button("Sample: Leet", use_container_width=True, type="secondary"):
                    st.session_state["active_text_val"] = "F.u.c.k this sh!t and all those d*mbasses pushing 1diot code into production!"
            with sp_c3:
                if st.button("Sample: Clean", use_container_width=True, type="secondary"):
                    st.session_state["active_text_val"] = "Artificial intelligence models analyze language patterns to promote safe and respectful digital communication."

            text_val = st.session_state.get("active_text_val") or loaded_text
            raw_text = st.text_area("Input/Raw Text", value=text_val, height=200, placeholder="Enter or paste text here, or upload a text, audio, or video file above.", label_visibility="collapsed")

            st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
            can_process = bool(raw_text.strip())
            process = st.button("Start Text Processing", type="primary", use_container_width=True, disabled=not can_process)

        render_mascot("text")

    with options_col:
        tab_mod, tab_rules, tab_norm = st.tabs([
            "Moderation & Rules",
            "Replacement Style",
            "Normalization",
        ])

        with tab_mod:
            text_selected_categories = render_category_selector("text")
            st.markdown("<div style='height:6px;'></div>", unsafe_allow_html=True)
            wl_c, bl_c = st.columns(2)
            with wl_c:
                whitelist = st.text_area("Whitelist", placeholder="Allowed words (e.g. god, damn)", height=110, key="text_whitelist_text")
            with bl_c:
                blacklist = st.text_area("Blacklist", placeholder="Forced censor words (e.g. idiot)", height=110, key="text_blacklist_text")

        with tab_rules:
            clean_standard = st.checkbox("Lexicon Matching", value=True, help="Detect standard profane words in dictionary.")
            clean_obfuscated = st.checkbox("Obfuscated / Leet Speak", value=True, help="Detect leet speak, character substitutions, and obscured profanity.")
            st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
            style_label = st.radio("Replacement Masking", ["****", "F***", "Custom"], horizontal=True)
            style = {"****": "A", "F***": "B", "Custom": "D"}[style_label]
            custom = st.text_input("Custom Replacement String", value="####", disabled=style != "D")

        with tab_norm:
            p1, p2 = st.columns(2)
            with p1:
                normalize_unicode = st.checkbox("Unicode Cleanup", value=True)
                expand_contractions = st.checkbox("Expand Contractions", value=False)
                remove_urls = st.checkbox("Remove URLs", value=False)
            with p2:
                compact_whitespace = st.checkbox("Compact Whitespace", value=False)
                casefold = st.checkbox("Casefold", value=False)
                remove_emails = st.checkbox("Remove Emails", value=False)

        options = {
            "selected_categories": text_selected_categories,
            "rating_preset": "Default",
            "clean_standard": clean_standard,
            "clean_obfuscated": clean_obfuscated,
            "censor_style": style,
            "custom_replacement": custom,
            "whitelist_text": whitelist,
            "blacklist_text": blacklist,
            "preprocess": {
                "normalize_unicode": normalize_unicode,
                "expand_contractions": expand_contractions,
                "compact_whitespace": compact_whitespace,
                "casefold": casefold,
                "remove_urls": remove_urls,
                "remove_emails": remove_emails,
            },
        }

    if process and can_process:
        if options["censor_style"] == "D" and not options["custom_replacement"].strip():
            st.error("Custom censor string cannot be empty.")
            return
        progress_slot = st.progress(0)
        status = StreamlitStatus(progress_slot, "text_logs")
        try:
            with st.spinner("Processing text..."):
                st.session_state.text_result = workflows.process_text_content(raw_text, options, uploaded_path, status)
            st.success("Text processing complete.")
        except Exception as exc:
            st.session_state.text_result = None
            st.error(str(exc))

    if st.session_state.text_result:
        with st.container():
            render_text_result(st.session_state.text_result)


def set_page(page_name: str) -> None:
    st.session_state.current_page = page_name


def main() -> None:
    init_state()
    
    with st.sidebar:
        st.markdown("<div class='section-label' style='margin-top:0.5rem;'>Navigation</div>", unsafe_allow_html=True)
        st.button("Home", use_container_width=True, type="primary" if st.session_state.current_page == "Home" else "secondary", on_click=set_page, args=("Home",))
        st.button("Media Moderation", use_container_width=True, type="primary" if st.session_state.current_page == "Media Moderation" else "secondary", on_click=set_page, args=("Media Moderation",))
        st.button("Text NLP Moderation", use_container_width=True, type="primary" if st.session_state.current_page == "Text NLP" else "secondary", on_click=set_page, args=("Text NLP",))
        st.button("Toxicity Detoxifier", use_container_width=True, type="primary" if st.session_state.current_page == "Toxicity Detoxifier" else "secondary", on_click=set_page, args=("Toxicity Detoxifier",))
        
        st.button("Toxicity Detection", use_container_width=True, type="primary" if st.session_state.current_page == "Toxicity Detection" else "secondary", on_click=set_page, args=("Toxicity Detection",))
    page = st.session_state.current_page
        
    render_header()
    
    if page == "Home":
        render_home_page()
    elif page == "Media Moderation":
        render_media_tab()
    elif page == "Text NLP":
        render_text_tab()
    elif page == "Toxicity Detoxifier":
        detoxifier_page.render_toxicity_tab()
    elif page == "Toxicity Detection":
        stream_toxicity_detection.render_toxicity_page()


if __name__ == "__main__":
    main()
