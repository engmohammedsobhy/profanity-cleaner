from __future__ import annotations

import html
import json
import mimetypes
import os
from pathlib import Path
from typing import Any, Dict, List

import streamlit as st
import streamlit.components.v1 as components

import streamlit_workflows as workflows

st.set_page_config(page_title="Purity — Profanity Cleaner", page_icon="✨", layout="wide")

st.markdown(
    """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
        
        :root {
            --bg-dark: #090d16;
            --panel-bg: rgba(17, 24, 39, 0.7);
            --panel-border: rgba(255, 255, 255, 0.08);
            --accent-teal: #10b981;
            --accent-indigo: #6366f1;
            --accent-cyan: #06b6d4;
            --text-main: #f3f4f6;
            --text-muted: #9ca3af;
            --card-radius: 16px;
        }

        html, body, [class*="css"] {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        }

        .stApp {
            background: linear-gradient(135deg, #070a12 0%, #0f172a 50%, #1e1b4b 100%);
            color: var(--text-main);
        }

        /* Glassmorphism Containers & Unified Spacing */
        [data-testid="stVerticalBlock"] > div {
            gap: 1.25rem !important;
        }
        
        div[data-testid="stForm"], div.stContainer > div {
            border-radius: var(--card-radius) !important;
        }

        [data-testid="stSidebar"] {
            background: rgba(15, 23, 42, 0.85) !important;
            backdrop-filter: blur(16px) !important;
            border-right: 1px solid var(--panel-border) !important;
        }

        /* Hero Title & Subheaders */
        .hero-title {
            font-size: 2.5rem;
            font-weight: 800;
            background: linear-gradient(135deg, #38bdf8 0%, #818cf8 50%, #c084fc 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            letter-spacing: -0.02em;
            margin-bottom: 0.25rem;
        }

        .hero-subtitle {
            color: var(--text-muted);
            font-size: 1.05rem;
            font-weight: 400;
            margin-bottom: 1.25rem;
        }

        .section-header {
            font-size: 1.15rem;
            font-weight: 700;
            color: var(--text-main);
            margin-bottom: 0.75rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }

        /* Cards & Metric Strips */
        .metric-card {
            background: rgba(30, 41, 59, 0.6);
            backdrop-filter: blur(12px);
            border: 1px solid var(--panel-border);
            border-left: 4px solid var(--accent-indigo);
            padding: 1.1rem 1.25rem;
            border-radius: 14px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
            transition: transform 0.2s ease, border-color 0.2s ease;
        }

        .metric-card:hover {
            transform: translateY(-2px);
            border-color: rgba(99, 102, 241, 0.4);
        }

        .metric-label {
            color: var(--text-muted);
            font-size: 0.825rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }

        .metric-value {
            font-size: 1.75rem;
            font-weight: 800;
            color: var(--text-main);
            margin-top: 0.25rem;
        }

        /* Primary Action Buttons */
        .stButton > button {
            border-radius: 12px !important;
            font-weight: 700 !important;
            font-size: 0.95rem !important;
            padding: 0.65rem 1.5rem !important;
            transition: all 0.25s ease-in-out !important;
            border: 1px solid rgba(99, 102, 241, 0.3) !important;
            background: linear-gradient(135deg, rgba(99, 102, 241, 0.2) 0%, rgba(168, 85, 247, 0.2) 100%) !important;
            color: #e0e7ff !important;
        }

        .stButton > button:hover {
            background: linear-gradient(135deg, #6366f1 0%, #a855f7 100%) !important;
            color: #ffffff !important;
            box-shadow: 0 6px 20px rgba(99, 102, 241, 0.4) !important;
            transform: translateY(-2px) !important;
            border-color: transparent !important;
        }

        /* Secondary Download Buttons */
        .stDownloadButton > button {
            border-radius: 10px !important;
            font-weight: 600 !important;
            border: 1px solid rgba(16, 185, 129, 0.3) !important;
            background: rgba(16, 185, 129, 0.1) !important;
            color: #34d399 !important;
        }

        .stDownloadButton > button:hover {
            background: #10b981 !important;
            color: #064e3b !important;
            box-shadow: 0 4px 15px rgba(16, 185, 129, 0.3) !important;
        }

        textarea, input, select {
            border-radius: 10px !important;
        }

        /* Custom Code Log Box */
        pre {
            background: rgba(15, 23, 42, 0.9) !important;
            border: 1px solid var(--panel-border) !important;
            border-radius: 12px !important;
            padding: 1rem !important;
            font-family: 'JetBrains Mono', monospace !important;
            font-size: 0.85rem !important;
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
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


class StreamlitStatus:
    def __init__(self, progress_slot: Any, log_slot: Any, state_key: str):
        self.progress_slot = progress_slot
        self.log_slot = log_slot
        self.state_key = state_key
        st.session_state[self.state_key] = []

    def emit(self, message: Any) -> None:
        if isinstance(message, (int, float)):
            value = max(0, min(100, int(message)))
            self.progress_slot.progress(value / 100)
            return
        text = str(message)
        st.session_state[self.state_key].append(text)
        self.log_slot.code("\n".join(st.session_state[self.state_key][-18:]) or "Ready")


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
                style='border:1px solid rgba(99,102,241,0.3);background:linear-gradient(135deg, #6366f1 0%, #a855f7 100%);color:#ffffff;border-radius:10px;padding:10px 14px;font-weight:700;cursor:pointer;width:100%;font-family:Inter,sans-serif;box-shadow: 0 4px 15px rgba(99,102,241,0.3);'>
            📋 Copy Cleaned Text
        </button>
        """,
        height=46,
    )


def render_mascot(state: str) -> None:
    path = workflows.backend.MASCOT_SVG_PATHS.get(state) if workflows.backend is not None and hasattr(workflows.backend, "MASCOT_SVG_PATHS") else ""
    if path and os.path.exists(path):
        st.image(path, use_container_width=True)


def compact_rows(rows: List[Dict[str, Any]], keys: List[str]) -> List[Dict[str, Any]]:
    return [{key: row.get(key) for key in keys} for row in rows]


def render_header() -> None:
    top_left, top_right = st.columns([0.75, 0.25], vertical_alignment="center")
    with top_left:
        st.markdown("<div class='hero-title'>Purity Profanity Cleaner</div>", unsafe_allow_html=True)
        st.markdown("<div class='hero-subtitle'>Advanced AI-powered profanity detection and media censorship platform.</div>", unsafe_allow_html=True)
    with top_right:
        render_mascot("startup")


def render_home_page() -> None:
    st.markdown("<div class='section-header'>🚀 Overview</div>", unsafe_allow_html=True)
    st.markdown("Purity provides data-driven, category-aware profanity moderation for text, audio, and video content.")
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    col1, col2 = st.columns(2, gap="large")
    with col1:
        with st.container(border=True):
            st.markdown("### 🎥 Media Moderation")
            st.markdown("""
            - **Whisper ASR Transcription:** High-accuracy word-level audio & video transcription.
            - **Millisecond Timestamp Detection:** Pinpoint profanity for exact audio muting or bleeping.
            - **Severity Rating Presets:** Tailor censoring using `Default`, `PG-13`, `R`, or `NC-17` presets.
            - **Export Formats:** Generate clean audio/video, JSON logs, and clean/raw SRT subtitles.
            """)
    with col2:
        with st.container(border=True):
            st.markdown("### 📝 Text NLP Moderation")
            st.markdown("""
            - **Document & Text Parsing:** Instant profanity analysis for text documents or raw input.
            - **Category-Aware Profiling:** Classifies flagged tokens into `MILD`, `MODERATE`, `STRONG`, and `VERY_SEVERE`.
            - **Custom Censor Styles:** Mask bad words with asterisks (`****`), initial-letter tags (`F***`), or custom strings.
            - **NLP Token Tables:** Full word-token breakdowns with POS tagging and detection sources.
            """)
            
    st.info("👈 Use the sidebar navigation menu to choose a moderation tool.")


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
    st.markdown("<div class='section-header'>📊 Processing Summary</div>", unsafe_allow_html=True)
    render_metric_grid(
        result.get("summary", {}),
        [
            ("Words", "word_count"),
            ("Profanity Hits", "profane_word_count"),
            ("Flagged Segments", "flagged_count"),
        ],
    )
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(result.get("summary_html", ""), unsafe_allow_html=True)

    st.markdown("<div class='section-header'>📥 Export Files</div>", unsafe_allow_html=True)
    downloads = st.columns(3)
    with downloads[0]:
        download_path(result.get("censored_path", ""), "Download Censored Media")
    with downloads[1]:
        download_path(result.get("log_path", ""), "Download JSON Log")
    with downloads[2]:
        if result.get("transcript_paths"):
            for name, path in result["transcript_paths"].items():
                download_path(path, f"Download {name.replace('_', ' ').title()}")

    st.markdown("<div class='section-header'>📋 Word Log</div>", unsafe_allow_html=True)
    flagged = [row for row in result.get("log", []) if row.get("is_profane")]
    table_rows = flagged or result.get("log", [])[:250]
    if table_rows:
        st.dataframe(
            compact_rows(table_rows, ["start_ms", "end_ms", "word", "is_profane"]),
            use_container_width=True,
            hide_index=True,
        )


def render_media_tab() -> None:
    st.markdown("<div class='section-header'>🎥 Media Moderation Pipeline</div>", unsafe_allow_html=True)
    input_col, options_col = st.columns([1.0, 1.0], gap="large")

    with input_col:
        with st.container(border=True):
            st.markdown("### 📤 Upload Media")
            uploaded_media = st.file_uploader("Input Media File", type=[ext.strip(".") for ext in workflows.MEDIA_EXTENSIONS], key="media_upload", label_visibility="collapsed")
            if uploaded_media:
                suffix = Path(uploaded_media.name).suffix.lower()
                _col1, media_center, _col3 = st.columns([1, 2, 1])
                with media_center:
                    if suffix in (".mp4", ".mkv", ".avi", ".mov"):
                        st.video(uploaded_media)
                    else:
                        st.audio(uploaded_media)
            render_mascot("media")

    with options_col:
        with st.container(border=True):
            st.markdown("### ⚙️ Moderation Settings")
            media_rating_preset = st.selectbox(
                "Profanity Severity Rating Preset",
                options=workflows.RATING_PRESETS,
                index=0,
                help="Default (strict censor), PG-13 (allows mild oaths), R (allows mild & moderate swearing), NC-17 (allows all except severe slurs).",
            )
            asr_label = st.selectbox("ASR Model (Whisper)", list(workflows.ASR_MODELS.keys()), index=1, help="Whisper model size: larger models offer higher transcription accuracy.")
            
            mode = st.radio("Censor Mode", ["sound", "silence"], index=0, horizontal=True)
            sound_map = {"Sine wave": "B", "Quack": "Q", "Dolphin": "D", "Triggered": "T", "Custom": "C"}
            sound_label = st.selectbox("Sound Choice", list(sound_map.keys()), disabled=mode != "sound")
            
            custom_sound_path = ""
            if sound_label == "Custom" and mode == "sound":
                uploaded_custom_sound = st.file_uploader("Upload Custom Audio (WAV/MP3)", type=["wav", "mp3", "ogg"], key="custom_sound")
                if uploaded_custom_sound:
                    custom_sound_path = workflows.save_uploaded_file(uploaded_custom_sound, "profanity_cleaner_custom")
                    
            censor_volume = st.slider("Censor Sound Volume (dB)", min_value=-30.0, max_value=30.0, value=0.0, step=1.0, disabled=mode != "sound", help="Adjust volume of the censor tone relative to original audio.")

        with st.container(border=True):
            st.markdown("### 📄 Transcript Export Options")
            out_cols = st.columns(5)
            with out_cols[0]:
                export_raw_txt = st.checkbox("Raw .txt", value=False)
            with out_cols[1]:
                export_clean_txt = st.checkbox("Clean .txt", value=False)
            with out_cols[2]:
                export_raw_srt = st.checkbox("Raw .srt", value=False)
            with out_cols[3]:
                export_clean_srt = st.checkbox("Clean .srt", value=False)
            with out_cols[4]:
                export_json = st.checkbox("Log .json", value=True)

        with st.container(border=True):
            st.markdown("### 🔍 Custom Word Overrides")
            words_a, words_b = st.columns(2)
            with words_a:
                whitelist = st.text_area("Media Whitelist", placeholder="words to allow", height=86)
            with words_b:
                blacklist = st.text_area("Media Blacklist", placeholder="words to force-censor", height=86)

        process = st.button("▶ Start Media Processing", type="primary", use_container_width=True, disabled=uploaded_media is None)

    if process and uploaded_media:
        progress_slot = st.progress(0)
        log_slot = st.empty()
        status = StreamlitStatus(progress_slot, log_slot, "media_logs")
        try:
            file_path = workflows.save_uploaded_file(uploaded_media, "profanity_cleaner_media")
            options = {
                "rating_preset": media_rating_preset,
                "asr_model": workflows.ASR_MODELS[asr_label],
                "mode": mode,
                "sound": sound_map[sound_label],
                "custom_sound_path": custom_sound_path,
                "censor_volume": censor_volume,
                "export_raw_txt": export_raw_txt,
                "export_clean_txt": export_clean_txt,
                "export_raw_srt": export_raw_srt,
                "export_clean_srt": export_clean_srt,
                "export_json_log": export_json,
                "whitelist_text": whitelist,
                "blacklist_text": blacklist,
            }
            with st.spinner("Processing media..."):
                st.session_state.media_result = workflows.process_media_file(file_path, options, status, status)
            st.success("Media processing complete.")
        except Exception as exc:
            st.session_state.media_result = None
            st.error(str(exc))

    if st.session_state.media_result:
        with st.container(border=True):
            render_media_result(st.session_state.media_result)


def text_options_panel() -> Dict[str, Any]:
    with st.container(border=True):
        st.markdown("### ⚙️ Rating & Censor Rules")
        text_rating_preset = st.selectbox(
            "Profanity Severity Preset",
            options=workflows.RATING_PRESETS,
            index=0,
            key="text_rating_preset",
            help="Default (strict censor), PG-13 (allows mild oaths), R (allows mild & moderate swearing), NC-17 (allows all except severe slurs).",
        )

        rules_col, style_col = st.columns([1, 1])
        with rules_col:
            st.markdown("**Detection Rules**")
            clean_standard = st.checkbox("Lexicon Matching", value=True)
            clean_obfuscated = st.checkbox("Obfuscated / Leet Speak", value=True)
        with style_col:
            st.markdown("**Censor Style**")
            style_label = st.radio("Replacement", ["****", "F***", "Custom"], horizontal=True)
            style = {"****": "A", "F***": "B", "Custom": "D"}[style_label]
            custom = st.text_input("Custom Replacement String", value="####", disabled=style != "D")

    with st.container(border=True):
        st.markdown("### 🧹 Preprocessing & Normalization")
        p1, p2, p3 = st.columns(3)
        with p1:
            normalize_unicode = st.checkbox("Unicode Cleanup", value=True)
            expand_contractions = st.checkbox("Expand Contractions", value=False)
        with p2:
            compact_whitespace = st.checkbox("Compact Whitespace", value=False)
            casefold = st.checkbox("Casefold", value=False)
        with p3:
            remove_urls = st.checkbox("Remove URLs", value=False)
            remove_emails = st.checkbox("Remove Emails", value=False)

    with st.container(border=True):
        st.markdown("### 🔍 Custom Word Overrides")
        wl_col, bl_col = st.columns(2)
        with wl_col:
            whitelist = st.text_area("Text Whitelist", placeholder="words to allow", height=82)
        with bl_col:
            blacklist = st.text_area("Text Blacklist", placeholder="words to force-censor", height=82)

    return {
        "rating_preset": text_rating_preset,
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


def render_text_result(result: Dict[str, Any]) -> None:
    if not result:
        return
    st.markdown("<div class='section-header'>📊 Analysis & Cleaned Output</div>", unsafe_allow_html=True)
    stats = result.get("stats", {})
    render_metric_grid(
        stats,
        [
            ("Word Count", "word_count"),
            ("Unique Terms", "unique_terms"),
            ("Profanity Hits", "profane_word_count"),
            ("Sentences", "sentence_count"),
        ],
    )
    st.markdown("<br>", unsafe_allow_html=True)

    result_cols = st.columns([0.7, 0.3])
    with result_cols[0]:
        st.text_area("Cleaned Output Text", value=result.get("cleaned_text", ""), height=220)
    with result_cols[1]:
        render_copy_button(result.get("cleaned_text", ""))
        st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
        st.download_button("📥 Download Cleaned Text", result.get("cleaned_text", "").encode("utf-8"), file_name="profanity_cleaned_text.txt", mime="text/plain", use_container_width=True)
        st.download_button(
            "📥 Download NLP JSON",
            json.dumps(result, indent=2, ensure_ascii=False).encode("utf-8"),
            file_name="profanity_text_analysis.json",
            mime="application/json",
            use_container_width=True,
        )
        if result.get("output_path"):
            download_path(result["output_path"], "Download Saved File")

    st.markdown("<div class='section-header'>📋 Data Breakdown</div>", unsafe_allow_html=True)
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
            st.markdown("**Top Frequent Terms**")
            st.dataframe(top_terms, use_container_width=True, hide_index=True)
        with right:
            st.markdown("**POS Tag Distribution**")
            st.dataframe(pos_counts, use_container_width=True, hide_index=True)


def render_text_tab() -> None:
    st.markdown("<div class='section-header'>📝 Text NLP Moderation Pipeline</div>", unsafe_allow_html=True)
    input_col, options_col = st.columns([1.0, 1.0], gap="large")
    
    with input_col:
        with st.container(border=True):
            st.markdown("### 📄 Input Text")
            uploaded_text = st.file_uploader("Upload Text File", type=[ext.strip(".") for ext in workflows.TEXT_EXTENSIONS], key="text_upload", label_visibility="collapsed")
            uploaded_path = ""
            loaded_text = ""
            if uploaded_text:
                uploaded_path = workflows.save_uploaded_file(uploaded_text, "profanity_cleaner_text")
                loaded_text = workflows.read_text_file(uploaded_path)

            raw_text = st.text_area("Input/Raw Text", value=loaded_text, height=270, placeholder="Enter text here or load a file above.", label_visibility="collapsed")
    
    with options_col:
        options = text_options_panel()
        can_process = bool(raw_text.strip())
        process = st.button("▶ Start Text Processing", type="primary", use_container_width=True, disabled=not can_process)

    if process and can_process:
        if options["censor_style"] == "D" and not options["custom_replacement"].strip():
            st.error("Custom censor string cannot be empty.")
            return
        progress_slot = st.progress(0)
        log_slot = st.empty()
        status = StreamlitStatus(progress_slot, log_slot, "text_logs")
        try:
            with st.spinner("Processing text..."):
                st.session_state.text_result = workflows.process_text_content(raw_text, options, uploaded_path, status)
            st.success("Text processing complete.")
        except Exception as exc:
            st.session_state.text_result = None
            st.error(str(exc))

    if st.session_state.text_result:
        with st.container(border=True):
            render_text_result(st.session_state.text_result)


def set_page(page_name: str) -> None:
    st.session_state.current_page = page_name


def main() -> None:
    init_state()
    
    with st.sidebar:
        st.markdown("<h2 style='font-size: 1.25rem; font-weight: 700;'>🧭 Navigation</h2>", unsafe_allow_html=True)
        st.button("🏠 Home Overview", use_container_width=True, type="primary" if st.session_state.current_page == "Home" else "secondary", on_click=set_page, args=("Home",))
        st.button("🎥 Media Moderation", use_container_width=True, type="primary" if st.session_state.current_page == "Media Moderation" else "secondary", on_click=set_page, args=("Media Moderation",))
        st.button("📝 Text NLP Moderation", use_container_width=True, type="primary" if st.session_state.current_page == "Text NLP" else "secondary", on_click=set_page, args=("Text NLP",))
        
    page = st.session_state.current_page
        
    render_header()
    
    if page == "Home":
        render_home_page()
    elif page == "Media Moderation":
        render_media_tab()
    elif page == "Text NLP":
        render_text_tab()


if __name__ == "__main__":
    main()
