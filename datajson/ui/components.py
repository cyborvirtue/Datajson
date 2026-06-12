from __future__ import annotations

import base64
import html
from pathlib import Path
from typing import Any

import streamlit as st

from datajson.blocks import flatten_fields, preview_value, summarize_sample
from datajson.config import APP_TITLE
from datajson.models import DatasetInfo, RenderBlock
from datajson.ui.theme import svg_icon


def render_topbar(path: Path) -> None:
    safe_path = html.escape(str(path))
    st.markdown(
        f"""
<div class="app-topbar">
  <div class="app-title">
    <span class="brand-mark">{svg_icon("database", 20)}</span>
    <span>{APP_TITLE} multimodal dataset viewer</span>
  </div>
  <div class="path-line notranslate" translate="no">{safe_path}</div>
</div>
        """,
        unsafe_allow_html=True,
    )


def render_metrics(info: DatasetInfo, index: int, blocks: list[RenderBlock], path: Path) -> None:
    missing_count = sum(1 for block in blocks if block.kind == "missing_image")
    image_count = sum(1 for block in blocks if block.kind in {"image", "missing_image"})
    size_bytes = info.size_bytes or path.stat().st_size
    size_mb = size_bytes / 1024 / 1024
    cards = [
        ("format", info.format_name.upper()),
        ("sample", f"{index + 1:,} / {info.sample_count:,}"),
        ("blocks", f"{len(blocks):,} total"),
        ("images", f"{image_count:,} / {missing_count:,} missing"),
    ]
    html_cards = "".join(
        f'<div class="metric-card notranslate" translate="no"><span>{html.escape(label)}</span><strong>{html.escape(value)}</strong></div>'
        for label, value in cards
    )
    st.markdown(f'<div class="metric-row">{html_cards}</div>', unsafe_allow_html=True)
    size_label = "Dataset size" if info.source_count > 1 or path.is_dir() else "File size"
    caption = f"{size_label}: {size_mb:.2f} MB"
    if info.parse_note:
        caption = f"{caption} · {info.parse_note}"
    st.caption(caption)


def render_sample_meta(sample: Any) -> None:
    items = summarize_sample(sample)
    if not items:
        return
    chips = "".join(
        f'<span class="meta-chip notranslate" translate="no"><b>{html.escape(key)}</b> {html.escape(value)}</span>' for key, value in items
    )
    st.markdown(f'<div class="sample-meta">{chips}</div>', unsafe_allow_html=True)


def render_block_header(block: RenderBlock, idx: int) -> None:
    if block.kind == "missing_image":
        badge_text = svg_icon("missing", 15)
    elif block.kind == "text":
        badge_text = svg_icon("text", 15)
    else:
        badge_text = svg_icon("image", 15)
    missing_class = " missing" if block.kind == "missing_image" else ""
    role = f'<span class="role-pill">{html.escape(block.role)}</span>' if block.role else ""
    label = f'<span class="role-pill">{html.escape(block.label)}</span>' if block.label else ""
    title = block.schema_name or block.kind
    st.markdown(
        f"""
<div class="block-head notranslate" translate="no">
  <div class="block-title">
    <span class="kind-badge{missing_class}">{badge_text}</span>
    <strong>{idx + 1:02d} · {html.escape(title)}</strong>
    {role}
    {label}
  </div>
  <div class="json-path">{html.escape(block.json_path)}</div>
</div>
        """,
        unsafe_allow_html=True,
    )


def render_text_block(block: RenderBlock) -> None:
    text = html.escape(str(block.value))
    st.markdown(f'<div class="text-body" translate="yes">{text}</div>', unsafe_allow_html=True)


def render_missing_image(block: RenderBlock, image_width: int, fit_images: bool) -> None:
    assert block.image is not None
    raw = html.escape(block.image.raw)
    resolved = html.escape(block.image.resolved or "")
    width_style = "max-width: 100%;" if fit_images else f"max-width: {image_width}px;"
    st.markdown(
        f"""
<div class="missing-box notranslate" translate="no" style="{width_style}">
  <div class="missing-inner">
    <div class="missing-icon"></div>
    <strong>Image path detected, but the file is missing.</strong>
    <code>{raw}</code>
    <div class="small-muted" style="margin-top: 8px;">resolved candidate: {resolved}</div>
  </div>
</div>
        """,
        unsafe_allow_html=True,
    )


def render_image_block(block: RenderBlock, image_width: int, fit_images: bool) -> None:
    assert block.image is not None
    ref = block.image
    if ref.exists:
        if ref.resolved and ref.resolved.startswith("data:image/"):
            render_streamlit_image(decode_data_url(ref.resolved), image_width, fit_images)
        elif ref.is_url:
            render_streamlit_image(ref.raw, image_width, fit_images)
        elif ref.resolved:
            render_streamlit_image(ref.resolved, image_width, fit_images)
    else:
        render_missing_image(block, image_width, fit_images)
    status_class = "status-loaded" if ref.exists else "status-missing"
    note = html.escape("embedded image data" if ref.raw.startswith("data:image/") else ref.raw)
    resolved_value = "embedded image data" if (ref.resolved or "").startswith("data:image/") else ref.resolved or ""
    resolved = html.escape(resolved_value)
    status = html.escape(ref.status)
    st.markdown(
        f"""
<div class="image-note notranslate" translate="no">
  <span>{note}</span>
  <span class="status-pill {status_class}">{status}</span>
</div>
<div class="small-muted notranslate" translate="no">resolved: {resolved}</div>
        """,
        unsafe_allow_html=True,
    )


def decode_data_url(data_url: str) -> bytes:
    _, encoded = data_url.split(",", 1)
    return base64.b64decode(encoded)


def render_streamlit_image(image: Any, image_width: int, fit_images: bool) -> None:
    if fit_images:
        st.image(image, use_column_width=True)
    else:
        st.image(image, width=image_width)


def render_blocks(blocks: list[RenderBlock], image_width: int, fit_images: bool) -> None:
    if not blocks:
        st.info("No obvious text or image blocks were detected. Use the Raw JSON and Field tree tabs to inspect this sample.")
        return
    for idx, block in enumerate(blocks):
        with st.container(border=True):
            render_block_header(block, idx)
            if block.kind == "text":
                render_text_block(block)
            elif block.kind in {"image", "missing_image"}:
                render_image_block(block, image_width, fit_images)
            else:
                st.code(preview_value(block.value), language="json")


def render_inspector(blocks: list[RenderBlock], sample: Any, image_root: str) -> None:
    missing_count = sum(1 for block in blocks if block.kind == "missing_image")
    st.markdown(f"### {svg_icon('anchor', 18)} JSON Anchors", unsafe_allow_html=True)
    st.caption(f"{len(blocks)} rendered blocks · {missing_count} missing images")
    for idx, block in enumerate(blocks[:80]):
        dot_class = " missing" if block.kind == "missing_image" else ""
        label = f"{block.schema_name or block.kind} block"
        path = block.json_path
        st.markdown(
            f"""
<div class="anchor-card notranslate" translate="no">
  <b><span class="anchor-dot{dot_class}"></span>{idx + 1:02d}. {html.escape(label)}</b>
  <code>{html.escape(path)}</code>
</div>
            """,
            unsafe_allow_html=True,
        )
    if len(blocks) > 80:
        st.caption(f"{len(blocks) - 80} more blocks omitted from the inspector.")
    st.markdown(f"### {svg_icon('image', 18)} Image root", unsafe_allow_html=True)
    st.code(image_root or "auto: JSON file folder + sample metadata image dirs")
    if isinstance(sample, dict) and "meta" in sample:
        st.markdown("### Meta")
        st.json(sample["meta"], expanded=False)


def render_field_tree(sample: Any) -> None:
    rows = flatten_fields(sample)
    st.dataframe(rows, use_container_width=True, hide_index=True)
    if len(rows) >= 500:
        st.caption("Field tree was truncated at 500 rows for UI responsiveness.")
