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

st.set_page_config(page_title="profanity detector", layout="wide")

st.markdown(
    """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=SF+Pro+Display:wght@400;500;600;700&family=Inter:wght@400;500;600;700&display=swap');
        
        :root {
            --bg-black: #000000;
            --card-bg: rgba(28, 28, 30, 0.68);
            --card-border: rgba(255, 255, 255, 0.08);
            --apple-blue: #0984e3;
            --apple-blue-hover: #2997ff;
            --text-primary: #f5f5f7;
            --text-secondary: #86868b;
            --card-radius: 18px;
            --pill-radius: 980px;
        }

        html, body, [class*="css"] {
            font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", "Inter", sans-serif;
            -webkit-font-smoothing: antialiased;
        }

        .stApp {
            background: #000000;
            background-image: radial-gradient(circle at 50% -20%, #1c1c1e 0%, #000000 80%);
            color: var(--text-primary);
        }

        /* Narrow Middle Spacing and Compact Gaps */
        [data-testid="stVerticalBlock"] > div {
            gap: 0.85rem !important;
        }
        
        div[data-testid="stForm"], div.stContainer > div {
            background: var(--card-bg) !important;
            backdrop-filter: blur(25px) !important;
            -webkit-backdrop-filter: blur(25px) !important;
            border: 1px solid var(--card-border) !important;
            border-radius: var(--card-radius) !important;
            padding: 1.1rem 1.25rem !important;
        }

        [data-testid="stSidebar"] {
            background: rgba(0, 0, 0, 0.85) !important;
            backdrop-filter: blur(30px) !important;
            -webkit-backdrop-filter: blur(30px) !important;
            border-right: 1px solid var(--card-border) !important;
        }

        /* Apple Headline Typography */
        .apple-title {
            font-size: 2.4rem;
            font-weight: 700;
            color: #ffffff;
            letter-spacing: -0.03em;
            margin-bottom: 0.2rem;
        }

        .apple-subtitle {
            color: var(--text-secondary);
            font-size: 1.0rem;
            font-weight: 400;
            letter-spacing: -0.01em;
            margin-bottom: 1.2rem;
        }

        .section-label {
            font-size: 0.75rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            color: var(--text-secondary);
            margin-bottom: 0.6rem;
        }

        /* Apple Metric Strips */
        .metric-card {
            background: rgba(44, 44, 46, 0.5);
            backdrop-filter: blur(20px);
            border: 1px solid var(--card-border);
            padding: 1.0rem 1.2rem;
            border-radius: 14px;
            box-shadow: 0 4px 16px rgba(0, 0, 0, 0.4);
            transition: transform 0.2s ease, border-color 0.2s ease;
        }

        .metric-card:hover {
            border-color: rgba(255, 255, 255, 0.18);
        }

        .metric-label {
            color: var(--text-secondary);
            font-size: 0.75rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.06em;
        }

        .metric-value {
            font-size: 1.6rem;
            font-weight: 700;
            color: var(--text-primary);
            margin-top: 0.2rem;
            letter-spacing: -0.02em;
        }

        /* Apple Pill Buttons */
        .stButton > button {
            border-radius: var(--pill-radius) !important;
            font-weight: 600 !important;
            font-size: 0.9rem !important;
            padding: 0.6rem 1.4rem !important;
            transition: all 0.2s ease-in-out !important;
            border: 1px solid transparent !important;
            background: #0071e3 !important;
            color: #ffffff !important;
            letter-spacing: -0.01em !important;
        }

        .stButton > button:hover {
            background: #0077ed !important;
            color: #ffffff !important;
            box-shadow: 0 4px 14px rgba(0, 113, 227, 0.4) !important;
            transform: scale(1.01) !important;
        }

        .stButton > button:disabled {
            background: rgba(255, 255, 255, 0.08) !important;
            color: var(--text-secondary) !important;
            border-color: transparent !important;
        }

        /* Secondary Download Buttons */
        .stDownloadButton > button {
            border-radius: var(--pill-radius) !important;
            font-weight: 600 !important;
            border: 1px solid rgba(255, 255, 255, 0.12) !important;
            background: rgba(255, 255, 255, 0.06) !important;
            color: var(--text-primary) !important;
        }

        .stDownloadButton > button:hover {
            background: rgba(255, 255, 255, 0.15) !important;
            border-color: rgba(255, 255, 255, 0.25) !important;
            color: #ffffff !important;
        }

        textarea, input, select {
            border-radius: 10px !important;
            background: rgba(0, 0, 0, 0.3) !important;
            border: 1px solid var(--card-border) !important;
            color: var(--text-primary) !important;
        }

        /* Code Log Output */
        pre {
            background: rgba(18, 18, 18, 0.95) !important;
            border: 1px solid var(--card-border) !important;
            border-radius: 12px !important;
            padding: 0.9rem !important;
            font-family: -apple-system, BlinkMacSystemFont, "SF Mono", monospace !important;
            font-size: 0.8rem !important;
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
                style='border:1px solid rgba(255,255,255,0.12);background:rgba(255,255,255,0.08);color:#f5f5f7;border-radius:980px;padding:9px 14px;font-weight:600;cursor:pointer;width:100%;font-family:-apple-system,BlinkMacSystemFont,sans-serif;font-size:0.85rem;'>
            Copy Cleaned Text
        </button>
        """,
        height=44,
    )


def render_mascot(state: str) -> None:
    path = workflows.backend.MASCOT_SVG_PATHS.get(state) if workflows.backend is not None and hasattr(workflows.backend, "MASCOT_SVG_PATHS") else ""
    if path and os.path.exists(path):
        st.image(path, use_container_width=True)


def compact_rows(rows: List[Dict[str, Any]], keys: List[str]) -> List[Dict[str, Any]]:
    return [{key: row.get(key) for key in keys} for row in rows]


def render_header() -> None:
    top_left, top_right = st.columns([0.8, 0.2], vertical_alignment="center")
    with top_left:
        st.markdown("<div class='apple-title'>profanity detector</div>", unsafe_allow_html=True)
        st.markdown("<div class='apple-subtitle'>Intelligent media moderation and text profanity analysis.</div>", unsafe_allow_html=True)
    with top_right:
        render_mascot("startup")


def render_home_page() -> None:
    st.markdown("<div class='section-label'>System Overview</div>", unsafe_allow_html=True)
    
    col1, col2 = st.columns(2, gap="small")
    with col1:
        with st.container(border=True):
            st.markdown("#### Media Moderation")
            st.markdown("""
            - Automatic speech transcription with Whisper.
            - Precise timestamp profanity muting or audio replacing.
            - Customizable severity rating presets.
            - Full subtitle SRT and JSON log exports.
            """)
    with col2:
        with st.container(border=True):
            st.markdown("#### Text NLP Moderation")
            st.markdown("""
            - Multi-level profanity and obfuscation identification.
            - Category severity mapping for flagged terms.
            - Customizable masking styles and replacement options.
            - POS tag analytics and token dataset tables.
            """)


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
    if censored_path and os.path.exists(censored_path):
        st.markdown("<div class='section-label'>Censored Media Preview</div>", unsafe_allow_html=True)
        ext = Path(censored_path).suffix.lower()
        if ext in [".mp4", ".mkv", ".avi", ".mov", ".webm"]:
            st.video(censored_path)
        else:
            st.audio(censored_path)

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

    st.markdown("<div class='section-label'>Word Logs</div>", unsafe_allow_html=True)
    flagged = [row for row in result.get("log", []) if row.get("is_profane")]
    table_rows = flagged or result.get("log", [])[:250]
    if table_rows:
        st.dataframe(
            compact_rows(table_rows, ["start_ms", "end_ms", "word", "is_profane"]),
            use_container_width=True,
            hide_index=True,
        )


def render_media_tab() -> None:
    st.markdown("<div class='section-label'>Media Processing</div>", unsafe_allow_html=True)
    input_col, options_col = st.columns([1.0, 1.0], gap="small")

    with input_col:
        with st.container(border=True):
            st.markdown("#### Input File")
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

        with st.container(border=True):
            st.markdown("#### Word Overrides")
            words_a, words_b = st.columns(2)
            with words_a:
                whitelist = st.text_area("Whitelist", placeholder="Allowed words", height=82)
            with words_b:
                blacklist = st.text_area("Blacklist", placeholder="Forced censor words", height=82)

    with options_col:
        with st.container(border=True):
            st.markdown("#### Moderation & Audio")
            media_rating_preset = st.selectbox(
                "Severity Rating Preset",
                options=workflows.RATING_PRESETS,
                index=0,
                help="Default (strict censor), PG-13 (allows mild oaths), R (allows mild & moderate swearing), NC-17 (allows all except severe slurs).",
            )
            asr_label = st.selectbox("ASR Model (Whisper)", list(workflows.ASR_MODELS.keys()), index=1, help="Whisper model size: larger models offer higher transcription accuracy.")
            
            censor_style_choice = st.radio(
                "Censoring style",
                options=["Silence", "One sound", "Multiple sounds"],
                index=1,
                horizontal=True,
            )

            mode_map = {
                "Silence": "silence",
                "One sound": "sound",
                "Multiple sounds": "multiple_sounds",
            }
            mode = mode_map[censor_style_choice]

            sound_map = {
                "Sine wave": "B",
                "Quack": "Q",
                "Dolphin": "D",
                "Triggered": "T",
                "Custom": "C",
            }

            sound_choice_keys = []
            custom_sound_path = ""

            if mode == "sound":
                selected_sound = st.selectbox("Sound Choice", list(sound_map.keys()))
                sound_choice_keys = [sound_map[selected_sound]]
                if selected_sound == "Custom":
                    uploaded_custom_sound = st.file_uploader("Upload Custom Audio (WAV/MP3)", type=["wav", "mp3", "ogg"], key="custom_sound")
                    if uploaded_custom_sound:
                        custom_sound_path = workflows.save_uploaded_file(uploaded_custom_sound, "profanity_cleaner_custom")

            elif mode == "multiple_sounds":
                selected_sounds = st.multiselect(
                    "Sound Choices (Randomly selected per profane word)",
                    options=list(sound_map.keys()),
                    default=["Sine wave", "Quack", "Dolphin"],
                )
                sound_choice_keys = [sound_map[s] for s in selected_sounds]
                if "Custom" in selected_sounds:
                    uploaded_custom_sound = st.file_uploader("Upload Custom Audio (WAV/MP3)", type=["wav", "mp3", "ogg"], key="custom_sound_multi")
                    if uploaded_custom_sound:
                        custom_sound_path = workflows.save_uploaded_file(uploaded_custom_sound, "profanity_cleaner_custom")

            overlap_censor = False
            marked_audio_volume = 100.0

            if mode in ["sound", "multiple_sounds"]:
                c1, c2 = st.columns(2)
                with c1:
                    overlap_censor = st.checkbox("Overlap censor audio", value=False, help="Make original audio heard together with the censor sound.")
                with c2:
                    marked_audio_volume = st.slider(
                        "Marked audio volume",
                        min_value=0,
                        max_value=100,
                        value=100,
                        step=1,
                        disabled=not overlap_censor,
                        help="Original audio volume level (0-100%) when censor sound plays.",
                    )

                censor_volume = st.slider("Censor Sound Volume (dB)", min_value=-30.0, max_value=30.0, value=0.0, step=1.0)
            else:
                censor_volume = 0.0

            use_padding = st.checkbox("Time padding", value=True, help="Pad censoring timeframe before and after each flagged word.")
            padding_before_sec = 0.05
            padding_after_sec = 0.05
            if use_padding:
                pad_c1, pad_c2 = st.columns(2)
                with pad_c1:
                    padding_before_sec = st.number_input("Before (sec)", min_value=0.00, max_value=2.00, value=0.05, step=0.01, format="%.2f")
                with pad_c2:
                    padding_after_sec = st.number_input("After (sec)", min_value=0.00, max_value=2.00, value=0.05, step=0.01, format="%.2f")

        with st.container(border=True):
            st.markdown("#### Transcript Exports")
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

        process = st.button("Start Media Processing", type="primary", use_container_width=True, disabled=uploaded_media is None)

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
                "sound": sound_choice_keys if mode == "multiple_sounds" else (sound_choice_keys[0] if sound_choice_keys else "B"),
                "custom_sound_path": custom_sound_path,
                "censor_volume": censor_volume,
                "overlap_censor": overlap_censor,
                "marked_audio_volume": marked_audio_volume,
                "padding_before_ms": int(padding_before_sec * 1000) if use_padding else 0,
                "padding_after_ms": int(padding_after_sec * 1000) if use_padding else 0,
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


def text_options_panel(whitelist_col: Any, blacklist_col: Any) -> Dict[str, Any]:
    with st.container(border=True):
        st.markdown("#### Rating & Rules")
        text_rating_preset = st.selectbox(
            "Severity Rating Preset",
            options=workflows.RATING_PRESETS,
            index=0,
            key="text_rating_preset",
            help="Default (strict censor), PG-13 (allows mild oaths), R (allows mild & moderate swearing), NC-17 (allows all except severe slurs).",
        )

        rules_col, style_col = st.columns([1, 1])
        with rules_col:
            st.markdown("<div class='section-label'>Rules</div>", unsafe_allow_html=True)
            clean_standard = st.checkbox("Lexicon Matching", value=True)
            clean_obfuscated = st.checkbox("Obfuscated / Leet Speak", value=True)
        with style_col:
            st.markdown("<div class='section-label'>Style</div>", unsafe_allow_html=True)
            style_label = st.radio("Replacement", ["****", "F***", "Custom"], horizontal=True)
            style = {"****": "A", "F***": "B", "Custom": "D"}[style_label]
            custom = st.text_input("Custom String", value="####", disabled=style != "D")

    with st.container(border=True):
        st.markdown("#### Normalization")
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

    with whitelist_col:
        whitelist = st.text_area("Whitelist", placeholder="Allowed words", height=82)
    with blacklist_col:
        blacklist = st.text_area("Blacklist", placeholder="Forced censor words", height=82)

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
    st.markdown("<div class='section-label'>Results</div>", unsafe_allow_html=True)
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

    st.markdown("<div class='section-label'>Details</div>", unsafe_allow_html=True)
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
    st.markdown("<div class='section-label'>Text NLP Analysis</div>", unsafe_allow_html=True)
    input_col, options_col = st.columns([1.0, 1.0], gap="small")
    
    with input_col:
        with st.container(border=True):
            st.markdown("#### Input Text")
            uploaded_text = st.file_uploader("Upload Text File", type=[ext.strip(".") for ext in workflows.TEXT_EXTENSIONS], key="text_upload", label_visibility="collapsed")
            uploaded_path = ""
            loaded_text = ""
            if uploaded_text:
                uploaded_path = workflows.save_uploaded_file(uploaded_text, "profanity_cleaner_text")
                loaded_text = workflows.read_text_file(uploaded_path)

            raw_text = st.text_area("Input/Raw Text", value=loaded_text, height=250, placeholder="Enter text here or upload a file above.", label_visibility="collapsed")

        with st.container(border=True):
            st.markdown("#### Word Overrides")
            wl_c, bl_c = st.columns(2)
    
    with options_col:
        options = text_options_panel(wl_c, bl_c)
        can_process = bool(raw_text.strip())
        process = st.button("Start Text Processing", type="primary", use_container_width=True, disabled=not can_process)

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
        st.markdown("<div class='section-label' style='margin-top:0.5rem;'>Navigation</div>", unsafe_allow_html=True)
        st.button("Home", use_container_width=True, type="primary" if st.session_state.current_page == "Home" else "secondary", on_click=set_page, args=("Home",))
        st.button("Media Moderation", use_container_width=True, type="primary" if st.session_state.current_page == "Media Moderation" else "secondary", on_click=set_page, args=("Media Moderation",))
        st.button("Text NLP Moderation", use_container_width=True, type="primary" if st.session_state.current_page == "Text NLP" else "secondary", on_click=set_page, args=("Text NLP",))
        
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
