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

st.set_page_config(page_title="Profanity Cleaner", page_icon="??", layout="wide")

st.markdown(
    """
    <style>
        :root {
            --bg: #0a0c10;
            --panel: rgba(23, 27, 34, 0.6);
            --line: rgba(42, 48, 57, 0.5);
            --text: #eef2f7;
            --muted: #9aa4b2;
            --teal: #2dd4bf;
            --amber: #f59e0b;
            --rose: #fb7185;
        }
        .stApp { background: linear-gradient(135deg, #0a0c10 0%, #1a1f29 100%); color: var(--text); }
        h1, h2, h3 { letter-spacing: 0; font-weight: 700; }
        [data-testid="stSidebar"] { background: rgba(17,21,28,0.7); backdrop-filter: blur(10px); border-right: 1px solid var(--line); }
        .hero-title { font-size: 2.8rem; font-weight: 800; background: -webkit-linear-gradient(45deg, var(--teal), var(--amber)); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin: 0 0 .2rem 0; }
        .subtle { color: var(--muted); }
        .metric-strip { border: 1px solid var(--line); border-left: 4px solid var(--teal); padding: 1rem; background: var(--panel); backdrop-filter: blur(8px); border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
        .result-box { border: 1px solid var(--line); padding: 1rem; background: rgba(17,21,28,0.8); border-radius: 12px; }
        .stButton > button, .stDownloadButton > button { border-radius: 8px; font-weight: 700; transition: all 0.3s ease; border: 1px solid var(--teal); background: rgba(45, 212, 191, 0.1); color: var(--teal); }
        .stButton > button:hover, .stDownloadButton > button:hover { background: var(--teal); color: #0a0c10; box-shadow: 0 4px 15px rgba(45,212,191,0.4); transform: translateY(-2px); border-color: var(--teal); }
        textarea, input { border-radius: 8px !important; }
        pre { white-space: pre-wrap; border: 1px solid var(--line); padding: .8rem; border-radius: 12px; background: rgba(16,20,27,0.8); backdrop-filter: blur(8px); }
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
    st.download_button(label, file_bytes(path), file_name=os.path.basename(path), mime=mime or "application/octet-stream")


def render_copy_button(text: str) -> None:
    payload = json.dumps(text)
    components.html(
        f"""
        <button onclick='navigator.clipboard.writeText({payload})'
                style='border:1px solid #2a3039;background:#2dd4bf;color:#071015;border-radius:8px;padding:10px 14px;font-weight:700;cursor:pointer;width:100%;'>
            Copy Cleaned Text
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
    top_left, top_right = st.columns([0.7, 0.3], vertical_alignment="center")
    with top_left:
        st.markdown("<div class='hero-title'>Profanity Cleaner</div>", unsafe_allow_html=True)
        st.markdown("<span class='subtle'>Content moderation for media, transcripts, and word-level NLP analysis.</span>", unsafe_allow_html=True)
    with top_right:
        render_mascot("startup")


def render_sidebar() -> None:
    with st.sidebar:
        st.header("Runtime")
        if workflows.backend is None:
            st.error("Media backend unavailable")
            st.caption(workflows.BACKEND_IMPORT_ERROR)
        else:
            st.success("Media backend ready")
        st.divider()
        st.subheader("Defaults")
        st.caption(f"Toxicity threshold: {workflows.DEFAULT_TOXICITY_THRESHOLD:.2f}")
        st.caption("Text files: .txt, .docx")
        st.caption("Media files: mp4, mkv, avi, mov, mp3, wav, m4a")


def render_metric_grid(stats: Dict[str, Any], mapping: List[tuple[str, str]]) -> None:
    cols = st.columns(len(mapping))
    for col, (label, key) in zip(cols, mapping):
        with col:
            st.markdown(f"<div class='metric-strip'><div class='subtle'>{html.escape(label)}</div><h3>{stats.get(key, 0)}</h3></div>", unsafe_allow_html=True)


def render_media_result(result: Dict[str, Any]) -> None:
    if not result:
        return
    st.subheader("Media Results")
    render_metric_grid(
        result.get("summary", {}),
        [
            ("Words", "word_count"),
            ("Profanity", "profane_word_count"),
            ("Flagged", "flagged_count"),
        ],
    )
    st.markdown(result.get("summary_html", ""), unsafe_allow_html=True)

    downloads = st.columns(3)
    with downloads[0]:
        download_path(result.get("censored_path", ""), "Download Censored Media")
    with downloads[1]:
        download_path(result.get("log_path", ""), "Download JSON Log")
    with downloads[2]:
        if result.get("transcript_paths"):
            for name, path in result["transcript_paths"].items():
                download_path(path, f"Download {name.replace('_', ' ').title()}")

    flagged = [row for row in result.get("log", []) if row.get("is_profane")]
    table_rows = flagged or result.get("log", [])[:250]
    if table_rows:
        st.dataframe(
            compact_rows(table_rows, ["start_ms", "end_ms", "word", "is_profane"]),
            use_container_width=True,
            hide_index=True,
        )


def render_media_tab() -> None:
    st.subheader("Media Moderation")
    input_col, options_col = st.columns([1.0, 1.0], gap="large")

    with input_col:
        with st.container(border=True):
            st.markdown("### Upload Media")
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
            st.markdown("### Configuration")
            asr_label = st.radio("ASR Model", list(workflows.ASR_MODELS.keys()), index=1, horizontal=True)
            mode = st.radio("Censor Mode", ["sound", "silence"], index=0, horizontal=True)
            sound_map = {"Sine wave": "B", "Quack": "Q", "Dolphin": "D", "Triggered": "T", "Custom": "C"}
            sound_label = st.selectbox("Sound Choice", list(sound_map.keys()), disabled=mode != "sound")
            
            custom_sound_path = ""
            if sound_label == "Custom" and mode == "sound":
                uploaded_custom_sound = st.file_uploader("Upload Custom Audio (WAV/MP3)", type=["wav", "mp3", "ogg"], key="custom_sound")
                if uploaded_custom_sound:
                    custom_sound_path = workflows.save_uploaded_file(uploaded_custom_sound, "profanity_cleaner_custom")
                    
            censor_volume = st.slider("Censor Sound Volume (dB)", min_value=-30.0, max_value=30.0, value=0.0, step=1.0, disabled=mode != "sound", help="Adjust the volume of the censor sound relative to the original audio.")

        with st.container(border=True):
            st.markdown("### Transcript Output")
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
            st.markdown("### Filter Lists")
            words_a, words_b = st.columns(2)
            with words_a:
                whitelist = st.text_area("Media Whitelist", placeholder="hell damn", height=86)
            with words_b:
                blacklist = st.text_area("Media Blacklist", placeholder="custom words", height=86)

        process = st.button("Start Media Processing", type="primary", use_container_width=True, disabled=uploaded_media is None)

    if process and uploaded_media:
        progress_slot = st.progress(0)
        log_slot = st.empty()
        status = StreamlitStatus(progress_slot, log_slot, "media_logs")
        try:
            file_path = workflows.save_uploaded_file(uploaded_media, "profanity_cleaner_media")
            options = {
                "asr_model": workflows.ASR_MODELS[asr_label],
                "mode": mode,
                "sound": sound_map[sound_label],
                "custom_sound_path": custom_sound_path,
                "censor_volume": censor_volume,
                "censor_toxic": False,
                "analyze_toxicity": False,
                "toxicity_threshold": workflows.DEFAULT_TOXICITY_THRESHOLD,
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
        st.markdown("### Cleaning Rules & Style")
        rules_col, style_col, prep_col = st.columns([0.9, 0.85, 1.1])
        with rules_col:
            st.markdown("**Rules**")
            clean_standard = st.checkbox("Lexicon", value=True)
            clean_obfuscated = st.checkbox("Obfuscated", value=True)
            clean_toxicity = st.checkbox("Toxicity", value=False)
            toxicity_threshold = st.slider("Text Toxicity Threshold", 0.0, 1.0, workflows.DEFAULT_TOXICITY_THRESHOLD, 0.01, disabled=not clean_toxicity)
        with style_col:
            st.markdown("**Censor Style**")
            style_label = st.radio("Replacement", ["****", "F***", "Custom"], horizontal=True)
            style = {"****": "A", "F***": "B", "Custom": "D"}[style_label]
            custom = st.text_input("Custom String", value="####", disabled=style != "D")
        with prep_col:
            st.markdown("**NLP Preprocessing**")
            normalize_unicode = st.checkbox("Unicode Cleanup", value=True)
            expand_contractions = st.checkbox("Expand Contractions", value=False)
            compact_whitespace = st.checkbox("Compact Whitespace", value=False)
            casefold = st.checkbox("Casefold", value=False)
            remove_urls = st.checkbox("Remove URLs", value=False)
            remove_emails = st.checkbox("Remove Emails", value=False)

    with st.container(border=True):
        st.markdown("### Filter Lists")
        wl_col, bl_col = st.columns(2)
        with wl_col:
            whitelist = st.text_area("Text Whitelist", placeholder="words to allow", height=82)
        with bl_col:
            blacklist = st.text_area("Text Blacklist", placeholder="words to force-censor", height=82)

    return {
        "clean_standard": clean_standard,
        "clean_obfuscated": clean_obfuscated,
        "clean_toxicity": clean_toxicity,
        "toxicity_threshold": toxicity_threshold,
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
    st.subheader("Text Results")
    stats = result.get("stats", {})
    render_metric_grid(
        stats,
        [
            ("Words", "word_count"),
            ("Unique", "unique_terms"),
            ("Profanity", "profane_word_count"),
            ("Toxic", "toxic_sentence_count"),
        ],
    )

    result_cols = st.columns([0.7, 0.3])
    with result_cols[0]:
        st.text_area("Cleaned Text", value=result.get("cleaned_text", ""), height=230)
    with result_cols[1]:
        render_copy_button(result.get("cleaned_text", ""))
        st.download_button("Download Cleaned Text", result.get("cleaned_text", "").encode("utf-8"), file_name="profanity_cleaned_text.txt", mime="text/plain")
        st.download_button(
            "Download NLP JSON",
            json.dumps(result, indent=2, ensure_ascii=False).encode("utf-8"),
            file_name="profanity_text_analysis.json",
            mime="application/json",
        )
        if result.get("output_path"):
            download_path(result["output_path"], "Download Saved File")

    token_tab, flagged_tab, sent_tab, vocab_tab = st.tabs(["Word Tokens", "Flagged", "Sentences", "Vocabulary"])
    with token_tab:
        token_keys = ["index", "text", "normalized", "lemma", "pos_guess", "token_type", "start", "end", "is_stopword", "detection_source"]
        st.dataframe(compact_rows(result.get("word_tokens", []), token_keys), use_container_width=True, hide_index=True)
    with flagged_tab:
        flagged = result.get("flagged_tokens", [])
        if flagged:
            st.dataframe(compact_rows(flagged, ["text", "normalized", "lemma", "pos_guess", "is_obfuscated", "is_blacklisted", "detection_source", "replacement"]), use_container_width=True, hide_index=True)
        else:
            st.info("No flagged tokens.")
    with sent_tab:
        st.dataframe(compact_rows(result.get("sentences", []), ["index", "text", "word_count", "toxicity_score", "is_toxic", "replacement"]), use_container_width=True, hide_index=True)
    with vocab_tab:
        top_terms = [{"term": term, "count": count} for term, count in stats.get("top_terms", [])]
        pos_counts = [{"pos": pos, "count": count} for pos, count in stats.get("pos_counts", {}).items()]
        left, right = st.columns(2)
        with left:
            st.dataframe(top_terms, use_container_width=True, hide_index=True)
        with right:
            st.dataframe(pos_counts, use_container_width=True, hide_index=True)


def render_text_tab() -> None:
    st.subheader("Text NLP Moderation")
    input_col, options_col = st.columns([1.0, 1.0], gap="large")
    
    with input_col:
        with st.container(border=True):
            st.markdown("### Input Text")
            uploaded_text = st.file_uploader("Upload Text File", type=[ext.strip(".") for ext in workflows.TEXT_EXTENSIONS], key="text_upload", label_visibility="collapsed")
            uploaded_path = ""
            loaded_text = ""
            if uploaded_text:
                uploaded_path = workflows.save_uploaded_file(uploaded_text, "profanity_cleaner_text")
                loaded_text = workflows.read_text_file(uploaded_path)

            raw_text = st.text_area("Input/Raw Text", value=loaded_text, height=245, placeholder="Enter text here or load a file above.", label_visibility="collapsed")
    
    with options_col:
        options = text_options_panel()
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


def main() -> None:
    init_state()
    render_sidebar()
    render_header()
    media_tab, text_tab = st.tabs(["Media", "Text NLP"])
    with media_tab:
        render_media_tab()
    with text_tab:
        render_text_tab()


if __name__ == "__main__":
    main()
