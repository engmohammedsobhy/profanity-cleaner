import streamlit as st
import requests
import json
import os
import mimetypes

# Set this to the public IP / domain of your FastAPI server when deploying
API_URL = "http://localhost:8000"

st.set_page_config(page_title="Profanity Cleaner", page_icon="??", layout="wide")

st.markdown(
    """
    <style>
        :root {
            --bg: #0f1217;
            --panel: #171b22;
            --line: #2a3039;
            --text: #eef2f7;
            --muted: #9aa4b2;
            --teal: #2dd4bf;
            --amber: #f59e0b;
            --rose: #fb7185;
        }
        .stApp { background: var(--bg); color: var(--text); }
        h1, h2, h3 { letter-spacing: 0; }
        [data-testid="stSidebar"] { background: #11151c; border-right: 1px solid var(--line); }
        .hero-title { font-size: 2.35rem; font-weight: 780; margin: 0 0 .2rem 0; }
        .subtle { color: var(--muted); }
        .metric-strip { border: 1px solid var(--line); border-left: 4px solid var(--teal); padding: .8rem 1rem; background: var(--panel); border-radius: 8px; }
        .result-box { border: 1px solid var(--line); padding: 1rem; background: #11151c; border-radius: 8px; }
        .stButton > button, .stDownloadButton > button { border-radius: 8px; font-weight: 700; }
        textarea, input { border-radius: 8px !important; }
        pre { white-space: pre-wrap; border: 1px solid var(--line); padding: .8rem; border-radius: 8px; background: #10141b; }
    </style>
    """,
    unsafe_allow_html=True,
)

def download_path(path: str, label: str):
    if not path:
        return
    dl_url = f"{API_URL}/api/download?path={path}"
    try:
        response = requests.get(dl_url)
        if response.status_code == 200:
            mime, _ = mimetypes.guess_type(path)
            st.download_button(label, response.content, file_name=os.path.basename(path), mime=mime or "application/octet-stream")
        else:
            st.error(f"File not found on remote server: {os.path.basename(path)}")
    except Exception as e:
        st.error(f"Failed to fetch {label} from server.")

def render_media_tab():
    st.subheader("Media Moderation")
    input_col, options_col = st.columns([1.0, 1.0], gap="large")

    with input_col:
        with st.container(border=True):
            st.markdown("### Upload Media")
            uploaded_media = st.file_uploader("Input Media File", type=["mp4", "mkv", "avi", "mov", "mp3", "wav", "m4a"], key="media_upload", label_visibility="collapsed")
            if uploaded_media:
                suffix = os.path.splitext(uploaded_media.name)[1].lower()
                _col1, media_center, _col3 = st.columns([1, 2, 1])
                with media_center:
                    if suffix in (".mp4", ".mkv", ".avi", ".mov"):
                        st.video(uploaded_media)
                    else:
                        st.audio(uploaded_media)

    with options_col:
        with st.container(border=True):
            st.markdown("### Configuration")
            asr_label = st.radio("ASR Model", ["tiny.en", "base.en"], index=1, horizontal=True)
            mode = st.radio("Censor Mode", ["sound", "silence"], index=0, horizontal=True)
            sound_map = {"Sine wave": "B", "Quack": "Q", "Dolphin": "D", "Triggered": "T"}
            sound_label = st.selectbox("Sound Choice", list(sound_map.keys()), disabled=mode != "sound")

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
        with st.spinner("Processing media on remote API... This may take a while depending on the file size."):
            try:
                options = {
                    "asr_model": asr_label,
                    "mode": mode,
                    "sound": sound_map[sound_label],
                    "export_raw_txt": export_raw_txt,
                    "export_clean_txt": export_clean_txt,
                    "export_raw_srt": export_raw_srt,
                    "export_clean_srt": export_clean_srt,
                    "export_json_log": export_json,
                    "whitelist_text": whitelist,
                    "blacklist_text": blacklist,
                }
                files = {"file": (uploaded_media.name, uploaded_media.getvalue(), uploaded_media.type)}
                data = {"options": json.dumps(options)}
                response = requests.post(f"{API_URL}/api/process_media", files=files, data=data)
                if response.status_code == 200:
                    res_json = response.json()
                    if res_json.get("status") == "success":
                        st.session_state.media_result = res_json.get("data")
                        st.success("Media processing complete.")
                    else:
                        st.error(res_json.get("message"))
                else:
                    st.error(f"Server returned status {response.status_code}")
            except Exception as e:
                st.error(f"Connection error: Make sure the API server is running at {API_URL}. Error: {str(e)}")

    if st.session_state.get("media_result"):
        with st.container(border=True):
            result = st.session_state.media_result
            st.subheader("Media Results")
            # Metrics
            summary = result.get("summary", {})
            cols = st.columns(3)
            with cols[0]:
                st.markdown(f"<div class='metric-strip'><div class='subtle'>Words</div><h3>{summary.get('word_count', 0)}</h3></div>", unsafe_allow_html=True)
            with cols[1]:
                st.markdown(f"<div class='metric-strip'><div class='subtle'>Profanity</div><h3>{summary.get('profane_word_count', 0)}</h3></div>", unsafe_allow_html=True)
            with cols[2]:
                st.markdown(f"<div class='metric-strip'><div class='subtle'>Flagged</div><h3>{summary.get('flagged_count', 0)}</h3></div>", unsafe_allow_html=True)
            
            st.markdown(result.get("summary_html", ""), unsafe_allow_html=True)
            
            downloads = st.columns(3)
            with downloads[0]:
                download_path(result.get("censored_path", ""), "Download Censored Media")
            with downloads[1]:
                download_path(result.get("log_path", ""), "Download JSON Log")
            with downloads[2]:
                if result.get("transcript_paths"):
                    for name, path in result.get("transcript_paths", {}).items():
                        download_path(path, f"Download {name.replace('_', ' ').title()}")
            
            flagged = [row for row in result.get("log", []) if row.get("is_profane")]
            table_rows = flagged or result.get("log", [])[:250]
            if table_rows:
                st.dataframe(
                    [{k: row.get(k) for k in ["start_ms", "end_ms", "word", "is_profane"]} for row in table_rows],
                    use_container_width=True,
                    hide_index=True,
                )

def text_options_panel():
    with st.container(border=True):
        st.markdown("### Cleaning Rules & Style")
        rules_col, style_col, prep_col = st.columns([0.9, 0.85, 1.1])
        with rules_col:
            st.markdown("**Rules**")
            clean_standard = st.checkbox("Lexicon", value=True)
            clean_obfuscated = st.checkbox("Obfuscated", value=True)
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
        "clean_toxicity": False,
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

def render_text_tab():
    st.subheader("Text NLP Moderation")
    input_col, options_col = st.columns([1.0, 1.0], gap="large")
    
    with input_col:
        with st.container(border=True):
            st.markdown("### Input Text")
            raw_text = st.text_area("Input/Raw Text", height=245, placeholder="Enter text here.")
    
    with options_col:
        options = text_options_panel()
        can_process = bool(raw_text.strip())
        process = st.button("Start Text Processing", type="primary", use_container_width=True, disabled=not can_process)

    if process and can_process:
        with st.spinner("Processing text on remote API..."):
            try:
                response = requests.post(f"{API_URL}/api/process_text", json={"raw_text": raw_text, "options": options})
                if response.status_code == 200:
                    res_json = response.json()
                    if res_json.get("status") == "success":
                        st.session_state.text_result = res_json.get("data")
                        st.success("Text processing complete.")
                    else:
                        st.error(res_json.get("message"))
                else:
                    st.error(f"Server returned status {response.status_code}")
            except Exception as e:
                st.error(f"Connection error: Make sure the API server is running at {API_URL}. Error: {str(e)}")

    if st.session_state.get("text_result"):
        with st.container(border=True):
            result = st.session_state.text_result
            st.subheader("Text Results")
            
            stats = result.get("stats", {})
            cols = st.columns(3)
            with cols[0]:
                st.markdown(f"<div class='metric-strip'><div class='subtle'>Words</div><h3>{stats.get('word_count', 0)}</h3></div>", unsafe_allow_html=True)
            with cols[1]:
                st.markdown(f"<div class='metric-strip'><div class='subtle'>Unique</div><h3>{stats.get('unique_terms', 0)}</h3></div>", unsafe_allow_html=True)
            with cols[2]:
                st.markdown(f"<div class='metric-strip'><div class='subtle'>Profanity</div><h3>{stats.get('profane_word_count', 0)}</h3></div>", unsafe_allow_html=True)
            
            result_cols = st.columns([0.7, 0.3])
            with result_cols[0]:
                st.text_area("Cleaned Text", value=result.get("cleaned_text", ""), height=230)
            with result_cols[1]:
                st.download_button("Download Cleaned Text", result.get("cleaned_text", "").encode("utf-8"), file_name="profanity_cleaned_text.txt", mime="text/plain")
                st.download_button(
                    "Download NLP JSON",
                    json.dumps(result, indent=2, ensure_ascii=False).encode("utf-8"),
                    file_name="profanity_text_analysis.json",
                    mime="application/json",
                )
                download_path(result.get("output_path"), "Download Saved File")

def main():
    if "media_result" not in st.session_state:
        st.session_state.media_result = None
    if "text_result" not in st.session_state:
        st.session_state.text_result = None

    with st.sidebar:
        st.header("Runtime")
        st.info("Connected to FastAPI Backend API.")
        st.divider()
        st.subheader("Defaults")
        st.caption("Text files: .txt, .docx")
        st.caption("Media files: mp4, mkv, avi, mov, mp3, wav, m4a")

    top_left, top_right = st.columns([0.7, 0.3], vertical_alignment="center")
    with top_left:
        st.markdown("<div class='hero-title'>Profanity Cleaner Client</div>", unsafe_allow_html=True)
        st.markdown("<span class='subtle'>Content moderation via remote API.</span>", unsafe_allow_html=True)

    media_tab, text_tab = st.tabs(["Media", "Text NLP"])
    with media_tab:
        render_media_tab()
    with text_tab:
        render_text_tab()

if __name__ == "__main__":
    main()
