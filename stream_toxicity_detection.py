import os
import tempfile
import streamlit as st
from toxicity_detection_models import analyze_media_toxicity, analyze_text_toxicity


def display_toxicity_results(results: dict):
    """دالة مساعدة لعرض نتائج التحليل بشكل موحد تفصيلي"""
    st.subheader("Moderation Status")
    if results.get("is_safe", True):
        st.success("**SAFE CONTENT**: No toxicity violations detected for the selected threshold.")
    else:
        st.error("**VIOLATION DETECTED**")
        for item in results.get("violations", []):
            st.warning(f"• **{item['category']}**: {item['score']:.2f}%")

    probs = results.get("probabilities", {})
    if probs:
        st.markdown("---")
        st.subheader("Probability Breakdown by Category")
        col1, col2 = st.columns(2)
        categories_list = list(probs.items())
        half = (len(categories_list) + 1) // 2

        with col1:
            for cat, score in categories_list[:half]:
                st.write(f"**{cat}**: `{score:.2f}%`")
                st.progress(min(max(float(score) / 100.0, 0.0), 1.0))

        with col2:
            for cat, score in categories_list[half:]:
                st.write(f"**{cat}**: `{score:.2f}%`")
                st.progress(min(max(float(score) / 100.0, 0.0), 1.0))


def render_toxicity_page():
    st.title("Toxicity Detection & Moderation")
    st.write(
        "Analyze text, video, or audio files for toxicity and inappropriate content."
    )

    threshold_pct = st.slider(
        "Moderation Sensitivity Threshold (%)",
        min_value=10,
        max_value=90,
        value=70,
        step=5,
        help="Categories exceeding this probability threshold will trigger a violation alert."
    )
    threshold = threshold_pct / 100.0

    # إنشاء تبويبين: الأول للنصوص والثاني للوسائط
    tab_text, tab_media = st.tabs(
        ["Text Input Analysis", "Media File Analysis"]
    )

    # --- TABS 1: تحليل النصوص المباشرة ---
    with tab_text:
        st.subheader("Text Toxicity Analysis")
        user_text = st.text_area(
            "Enter text to analyze:",
            placeholder="Type your sentences here...",
            height=130,
        )

        if st.button("Analyze Text"):
            if not user_text.strip():
                st.warning("Please enter some text first.")
            else:
                with st.spinner("Analyzing text toxicity..."):
                    # استدعاء دالة تحليل النصوص من الموديل
                    text_results = analyze_text_toxicity(user_text, threshold=threshold)

                display_toxicity_results(text_results)

    # --- TABS 2: تحليل الملفات (صوت/فيديو) ---
    with tab_media:
        st.subheader("Audio / Video Toxicity Analysis")
        uploaded_file = st.file_uploader(
            "Choose a media file", type=["mp4", "mp3", "wav", "m4a", "mov"]
        )

        if uploaded_file is not None:
            file_ext = uploaded_file.name.split(".")[-1].lower()

            if file_ext in ["mp4", "mov"]:
                st.video(uploaded_file)
            else:
                st.audio(uploaded_file)

            if st.button("Analyze Media Toxicity"):
                with tempfile.NamedTemporaryFile(
                    delete=False, suffix=f".{file_ext}"
                ) as tmp_file:
                    tmp_file.write(uploaded_file.read())
                    temp_path = tmp_file.name

                with st.spinner("Transcribing and analyzing toxicity..."):
                    results = analyze_media_toxicity(temp_path, threshold=threshold)

                st.subheader("Transcribed Text")
                st.info(f'"{results["text"]}"')

                display_toxicity_results(results)

                if os.path.exists(temp_path):
                    os.remove(temp_path)


if __name__ == "__main__":
    render_toxicity_page()