from __future__ import annotations
 
import json
from typing import Any, Dict
 
import streamlit as st
import streamlit.components.v1 as components
 
import toxicity_detoxifier as detox
 

 
def _copy_button(text: str, label: str = "Copy Detoxified Text") -> None:
    payload = json.dumps(text or "")
    components.html(
        f"""
        <button onclick='navigator.clipboard.writeText({payload})'
                style='border:none;background:rgba(255,255,255,0.08);color:#f5f5f7;
                       border-radius:980px;padding:9px 14px;font-weight:600;
                       cursor:pointer;width:100%;
                       font-family:-apple-system,BlinkMacSystemFont,sans-serif;
                       font-size:0.85rem;'>
            {label}
        </button>
        """,
        height=44,
    )
 
 
def _init_toxicity_state() -> None:
    defaults = {
        "toxicity_result": None,
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)
 
 
def _render_score_grid(category_scores: Dict[str, float]) -> None:
    if not category_scores:
        reason = getattr(detox, "MODEL_LOAD_ERROR", None)
        if reason:
            st.error(f"Model not loaded — {reason}")
        else:
            st.info("No category scores available (model not loaded).")
        return
    cats = list(category_scores.items())
    cols = st.columns(len(cats))
    for col, (cat, score) in zip(cols, cats):
        with col:
            st.markdown(
                f"""
                <div class='metric-card'>
                    <div class='metric-label'>{cat.replace('_', ' ').title()}</div>
                    <div class='metric-value'>{score * 100:.1f}%</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
 
 
def _render_result(result: Dict[str, Any]) -> None:
    st.markdown("<div class='section-label'>Summary</div>", unsafe_allow_html=True)
 
    top_cat = result.get("top_category", "NONE")
    score = result.get("toxicity_score", 0.0)
    modified = result.get("was_modified", False)
 
    s1, s2, s3 = st.columns(3)
    with s1:
        st.markdown(
            f"""<div class='metric-card'><div class='metric-label'>Top Category</div>
            <div class='metric-value'>{top_cat}</div></div>""",
            unsafe_allow_html=True,
        )
    with s2:
        st.markdown(
            f"""<div class='metric-card'><div class='metric-label'>Toxicity Score</div>
            <div class='metric-value'>{score * 100:.1f}%</div></div>""",
            unsafe_allow_html=True,
        )
    with s3:
        st.markdown(
            f"""<div class='metric-card'><div class='metric-label'>Status</div>
            <div class='metric-value'>{'Modified' if modified else 'Unmodified'}</div></div>""",
            unsafe_allow_html=True,
        )
 
    st.markdown("<div style='height:14px;'></div>", unsafe_allow_html=True)
    st.markdown("<div class='section-label'>Category Breakdown</div>", unsafe_allow_html=True)
    _render_score_grid(result.get("category_scores", {}))
 
    st.markdown("<div style='height:14px;'></div>", unsafe_allow_html=True)
    st.markdown("<div class='section-label'>Detoxified Output</div>", unsafe_allow_html=True)
    with st.container():
        st.text_area(
            "Detoxified Text",
            value=result.get("detoxified_text", ""),
            height=140,
            label_visibility="collapsed",
            disabled=True,
        )
        _copy_button(result.get("detoxified_text", ""))
 
 
def render_toxicity_tab() -> None:
    _init_toxicity_state()

    with st.container():
        raw_text = st.text_area(
            "Input Text",
            key="detox_input_area",
            height=180,
            placeholder="Enter or paste a comment/message to analyze and detoxify.",
            label_visibility="collapsed",
        )

        st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)

        threshold = st.number_input(
            "Toxicity Threshold",
            min_value=0.0,
            max_value=1.0,
            value=0.60,
            step=0.05,
            format="%.2f",
            help="Comments scoring above this threshold get rewritten by the LLM.",
        )

        st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
        can_process = bool(raw_text.strip())
        process = st.button(
            "Analyze & Detoxify",
            type="primary",
            use_container_width=True,
            disabled=not can_process,
        )

    if process and can_process:
        with st.spinner("Analyzing and detoxifying text..."):
            try:
                st.session_state.toxicity_result = detox.end_to_end_detoxifier(raw_text, threshold=threshold)
                st.success("Analysis complete.")
            except Exception as exc:
                st.session_state.toxicity_result = None
                st.error(str(exc))

    current_result = st.session_state.get("toxicity_result")
    if current_result and current_result.get("original_text") == raw_text:
        with st.container():
            _render_result(current_result)