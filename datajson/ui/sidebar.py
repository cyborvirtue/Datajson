from __future__ import annotations

from pathlib import Path

import streamlit as st

from datajson.config import DEFAULT_JSONL
from datajson.json_store import (
    choose_auto_collection_path,
    file_stat,
    find_collection_candidates,
    infer_parser_mode,
    load_json_root,
)
from datajson.ui.theme import svg_icon


def sync_index(sample_count: int) -> int:
    if "sample_index" not in st.session_state:
        st.session_state.sample_index = 0
    if sample_count <= 0:
        st.session_state.sample_index = 0
    else:
        st.session_state.sample_index = min(max(int(st.session_state.sample_index), 0), sample_count - 1)
    return st.session_state.sample_index


def clamp_index(index: object, sample_count: int) -> int:
    if sample_count <= 0:
        return 0
    try:
        numeric = int(index)
    except (TypeError, ValueError):
        numeric = 0
    return min(max(numeric, 0), sample_count - 1)


def commit_sample_index(sample_count: int) -> None:
    st.session_state.sample_index = clamp_index(st.session_state.get("sample_index_input", 0), sample_count)


def sidebar_controls() -> tuple[Path, str, str, bool, str | None, int, bool]:
    st.sidebar.markdown(
        f'<div class="sidebar-title">{svg_icon("database", 20)}<span>Dataset</span></div>',
        unsafe_allow_html=True,
    )
    st.sidebar.selectbox(
        "Theme",
        ("dark", "light"),
        format_func=lambda value: "Dark console" if value == "dark" else "Light amethyst",
        key="theme_mode",
    )

    default_path = DEFAULT_JSONL if Path(DEFAULT_JSONL).exists() else ""
    path_text = st.sidebar.text_input("JSON / JSONL path", value=st.session_state.get("path_text", default_path))
    if path_text != st.session_state.get("path_text"):
        st.session_state.path_text = path_text
        st.session_state.sample_index = 0
        st.session_state.sample_index_input = 0
        st.session_state.collection_path = None

    parser_mode = st.sidebar.selectbox("Parser", ("auto", "jsonl", "json"), index=0)
    image_root = st.sidebar.text_input("Image root override", value=st.session_state.get("image_root", ""))
    st.session_state.image_root = image_root

    st.sidebar.markdown(f"### {svg_icon('settings', 17)} Display", unsafe_allow_html=True)
    show_inspector = st.sidebar.toggle("Show right inspector", value=True)
    fit_images = st.sidebar.toggle("Fit images to column", value=st.session_state.get("fit_images", False), key="fit_images")
    image_width = st.sidebar.slider(
        "Image width",
        min_value=180,
        max_value=1200,
        value=int(st.session_state.get("image_width", 520)),
        step=20,
        disabled=fit_images,
        help="Used when images are not fitted to the full column width.",
        key="image_width",
    )

    collection_override: str | None = None
    path = Path(path_text).expanduser()
    if path.exists() and infer_parser_mode(path, parser_mode) == "json":
        try:
            size, mtime_ns = file_stat(str(path))
            root = load_json_root(str(path), size, mtime_ns)
            candidates = find_collection_candidates(root)
            labels = ["$  (single JSON document)"] + [
                f"{candidate_path}  ({count} items, first: {first_type})"
                for candidate_path, count, first_type in candidates
                if candidate_path != "$"
            ]
            paths = ["$"] + [candidate_path for candidate_path, _, _ in candidates if candidate_path != "$"]
            auto_path = choose_auto_collection_path(root)
            default_idx = paths.index(auto_path) if auto_path in paths else 0
            saved = st.session_state.get("collection_path")
            if saved in paths:
                default_idx = paths.index(saved)
            selected_label = st.sidebar.selectbox("JSON sample collection", labels, index=default_idx)
            selected_idx = labels.index(selected_label)
            collection_override = paths[selected_idx]
            if collection_override != st.session_state.get("collection_path"):
                st.session_state.sample_index = 0
                st.session_state.sample_index_input = 0
            st.session_state.collection_path = collection_override
        except Exception as exc:
            st.sidebar.warning(f"Collection scan failed: {exc}")

    return path, parser_mode, image_root, show_inspector, collection_override, int(image_width), bool(fit_images)


def sample_navigation(sample_count: int) -> int:
    index = sync_index(sample_count)
    st.sidebar.markdown(f"### {svg_icon('anchor', 17)} Sample", unsafe_allow_html=True)
    if sample_count <= 0:
        st.sidebar.warning("No samples found.")
        return 0

    if st.session_state.get("_nav_sample_count") != sample_count:
        st.session_state.sample_index = clamp_index(st.session_state.get("sample_index", 0), sample_count)
        st.session_state.sample_index_input = st.session_state.sample_index
        st.session_state._nav_sample_count = sample_count

    col_prev, col_next = st.sidebar.columns(2)
    if col_prev.button("Prev", width="stretch", disabled=index <= 0):
        st.session_state.sample_index = max(index - 1, 0)
        st.session_state.sample_index_input = st.session_state.sample_index
        st.rerun()
    if col_next.button("Next", width="stretch", disabled=index >= sample_count - 1):
        st.session_state.sample_index = min(index + 1, sample_count - 1)
        st.session_state.sample_index_input = st.session_state.sample_index
        st.rerun()

    index = sync_index(sample_count)
    st.session_state.sample_index_input = clamp_index(st.session_state.get("sample_index_input", index), sample_count)
    st.sidebar.number_input(
        "Index",
        min_value=0,
        max_value=max(sample_count - 1, 0),
        step=1,
        key="sample_index_input",
        on_change=commit_sample_index,
        args=(sample_count,),
    )
    if st.sidebar.button("Go to index", type="primary", width="stretch"):
        commit_sample_index(sample_count)
        st.rerun()
    return sync_index(sample_count)
