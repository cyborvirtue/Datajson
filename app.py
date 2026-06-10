from __future__ import annotations

import streamlit as st

from datajson.blocks import build_render_blocks
from datajson.config import APP_TITLE
from datajson.history import record_path_history
from datajson.json_store import create_dataset_info, dumps_json, load_current_sample, sample_count_from_info
from datajson.ui.components import (
    render_blocks,
    render_field_tree,
    render_inspector,
    render_metrics,
    render_sample_meta,
    render_topbar,
)
from datajson.ui.sidebar import sample_navigation, sidebar_controls
from datajson.ui.theme import install_css


def main() -> None:
    st.set_page_config(page_title=APP_TITLE, page_icon="D", layout="wide", initial_sidebar_state="expanded")
    install_css(st.session_state.get("theme_mode", "dark"))

    path, parser_mode, image_root, show_inspector, collection_override, image_width, fit_images = sidebar_controls()
    if not str(path).strip():
        st.warning("Enter a local JSON or JSONL file path in the sidebar.")
        return
    if not path.exists():
        st.error(f"File does not exist: {path}")
        return
    if not path.is_file():
        st.error(f"Path is not a file: {path}")
        return

    try:
        info = create_dataset_info(path, parser_mode, collection_override)
    except Exception as exc:
        st.error(f"Failed to parse dataset: {exc}")
        return
    record_path_history(path)

    index = sample_navigation(sample_count_from_info(info))
    try:
        sample = load_current_sample(path, info, index)
    except Exception as exc:
        st.error(f"Failed to parse sample {index}: {exc}")
        return

    blocks = build_render_blocks(sample, path, image_root)
    render_topbar(path)
    render_metrics(info, index, blocks, path)
    render_sample_meta(sample)

    rendered_tab, raw_tab, fields_tab = st.tabs(("Rendered sample", "Raw JSON", "Field tree"))
    with rendered_tab:
        if show_inspector:
            main_col, inspector_col = st.columns([0.74, 0.26], gap="large")
            with main_col:
                render_blocks(blocks, image_width, fit_images)
            with inspector_col:
                render_inspector(blocks, sample, image_root)
        else:
            render_blocks(blocks, image_width, fit_images)

    with raw_tab:
        st.download_button(
            "Download current sample JSON",
            data=dumps_json(sample),
            file_name=f"sample_{index:06d}.json",
            mime="application/json",
        )
        st.json(sample, expanded=2)

    with fields_tab:
        render_field_tree(sample)


if __name__ == "__main__":
    main()
