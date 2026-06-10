from __future__ import annotations

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
  <div class="path-line">{safe_path}</div>
</div>
        """,
        unsafe_allow_html=True,
    )


def render_metrics(info: DatasetInfo, index: int, blocks: list[RenderBlock], path: Path) -> None:
    missing_count = sum(1 for block in blocks if block.kind == "missing_image")
    image_count = sum(1 for block in blocks if block.kind in {"image", "missing_image"})
    size_mb = path.stat().st_size / 1024 / 1024
    cards = [
        ("format", info.format_name.upper()),
        ("sample", f"{index + 1:,} / {info.sample_count:,}"),
        ("blocks", f"{len(blocks):,} total"),
        ("images", f"{image_count:,} / {missing_count:,} missing"),
    ]
    html_cards = "".join(
        f'<div class="metric-card"><span>{html.escape(label)}</span><strong>{html.escape(value)}</strong></div>'
        for label, value in cards
    )
    st.markdown(f'<div class="metric-row">{html_cards}</div>', unsafe_allow_html=True)
    st.caption(f"File size: {size_mb:.2f} MB")


def render_sample_meta(sample: Any) -> None:
    items = summarize_sample(sample)
    if not items:
        return
    chips = "".join(
        f'<span class="meta-chip"><b>{html.escape(key)}</b> {html.escape(value)}</span>' for key, value in items
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
<div class="block-head">
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
    st.markdown(f'<div class="text-body">{text}</div>', unsafe_allow_html=True)


def render_missing_image(block: RenderBlock, image_width: int, fit_images: bool) -> None:
    assert block.image is not None
    raw = html.escape(block.image.raw)
    resolved = html.escape(block.image.resolved or "")
    width_style = "max-width: 100%;" if fit_images else f"max-width: {image_width}px;"
    st.markdown(
        f"""
<div class="missing-box" style="{width_style}">
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
    width: int | str = "stretch" if fit_images else image_width
    if ref.exists:
        if ref.resolved and ref.resolved.startswith("data:image/"):
            st.image(ref.resolved, width=width)
        elif ref.is_url:
            st.image(ref.raw, width=width)
        elif ref.resolved:
            st.image(ref.resolved, width=width)
    else:
        render_missing_image(block, image_width, fit_images)
    status_class = "status-loaded" if ref.exists else "status-missing"
    note = html.escape(ref.raw)
    resolved = html.escape(ref.resolved or "")
    status = html.escape(ref.status)
    st.markdown(
        f"""
<div class="image-note">
  <span>{note}</span>
  <span class="status-pill {status_class}">{status}</span>
</div>
<div class="small-muted">resolved: {resolved}</div>
        """,
        unsafe_allow_html=True,
    )


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
<div class="anchor-card">
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
    st.dataframe(rows, width="stretch", hide_index=True)
    if len(rows) >= 500:
        st.caption("Field tree was truncated at 500 rows for UI responsiveness.")
