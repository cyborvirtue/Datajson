from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import unquote, urlparse

from datajson.config import IMAGE_EXTS, IMAGE_KEYS, TEXT_KEYS
from datajson.json_store import dumps_json
from datajson.models import ImageRef, RenderBlock


def preview_value(value: Any, limit: int = 180) -> str:
    if isinstance(value, str):
        text = value.replace("\n", " ").strip()
    else:
        try:
            text = dumps_json(value)
        except TypeError:
            text = repr(value)
        text = re.sub(r"\s+", " ", text).strip()
    if len(text) > limit:
        return text[: limit - 1] + "..."
    return text


def normalize_path_text(value: str) -> str:
    text = value.strip().strip("\"'")
    if text.startswith("file://"):
        return unquote(urlparse(text).path)
    return text


def is_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"}


def looks_like_image_string(value: str) -> bool:
    text = normalize_path_text(value)
    if text.startswith("data:image/"):
        return True
    parsed = urlparse(text)
    clean_path = parsed.path if parsed.scheme else text.split("?", 1)[0].split("#", 1)[0]
    return clean_path.lower().endswith(IMAGE_EXTS)


def key_suggests_image(key: str | None) -> bool:
    if not key:
        return False
    lower = key.lower()
    return lower in IMAGE_KEYS or any(token in lower for token in ("image", "photo", "picture"))


def key_suggests_text(key: str | None) -> bool:
    if not key:
        return False
    lower = key.lower()
    return lower in TEXT_KEYS or any(token in lower for token in ("caption", "prompt", "question"))


def discover_sample_image_dirs(sample: Any) -> list[str]:
    keys = {
        "source_image_dir",
        "image_dir",
        "images_dir",
        "img_dir",
        "image_root",
        "root",
        "media_dir",
    }
    found: list[str] = []

    def walk(value: Any, depth: int = 0) -> None:
        if depth > 4:
            return
        if isinstance(value, dict):
            for key, child in value.items():
                if key.lower() in keys and isinstance(child, str) and child.strip():
                    found.append(child.strip())
                elif isinstance(child, (dict, list)):
                    walk(child, depth + 1)
        elif isinstance(value, list):
            for child in value[:20]:
                walk(child, depth + 1)

    walk(sample)
    return found


def unique_paths(paths: Iterable[Path]) -> list[Path]:
    seen: set[str] = set()
    unique: list[Path] = []
    for path in paths:
        marker = str(path)
        if marker not in seen:
            seen.add(marker)
            unique.append(path)
    return unique


def resolve_image_ref(raw_value: str, json_file: Path, image_root: str, sample: Any) -> ImageRef:
    raw = normalize_path_text(raw_value)
    if raw.startswith("data:image/"):
        return ImageRef(raw=raw, exists=True, is_url=False, resolved=raw, status="embedded")
    if is_url(raw):
        return ImageRef(raw=raw, exists=True, is_url=True, resolved=raw, status="remote")

    raw_path = Path(raw).expanduser()
    if raw_path.is_absolute():
        exists = raw_path.exists()
        return ImageRef(raw=raw, exists=exists, is_url=False, resolved=str(raw_path), status="loaded" if exists else "missing")

    json_dir = json_file.parent
    roots: list[Path] = []
    if image_root.strip():
        roots.append(Path(image_root).expanduser())
    roots.append(json_dir)

    sample_dirs = discover_sample_image_dirs(sample)
    candidates: list[Path] = []
    for root in roots:
        candidates.append(root / raw_path)
        candidates.append(root / raw_path.name)
        for image_dir in sample_dirs:
            image_dir_path = Path(image_dir).expanduser()
            if image_dir_path.is_absolute():
                candidates.append(image_dir_path / raw_path)
                candidates.append(image_dir_path / raw_path.name)
            else:
                candidates.append(root / image_dir_path / raw_path)
                candidates.append(root / image_dir_path / raw_path.name)

    for candidate in unique_paths(candidates):
        if candidate.exists():
            return ImageRef(raw=raw, exists=True, is_url=False, resolved=str(candidate), status="loaded")

    fallback = str(unique_paths(candidates)[0]) if candidates else str(json_dir / raw_path)
    return ImageRef(raw=raw, exists=False, is_url=False, resolved=fallback, status="missing")


def first_existing_key(value: dict[str, Any], keys: Iterable[str]) -> Any:
    for key in keys:
        if key in value and value[key] not in (None, ""):
            return value[key]
    lower_map = {str(key).lower(): key for key in value.keys()}
    for key in keys:
        actual = lower_map.get(key.lower())
        if actual is not None and value[actual] not in (None, ""):
            return value[actual]
    return None


def block_from_image(
    raw: str,
    json_path: str,
    schema_name: str,
    json_file: Path,
    image_root: str,
    sample: Any,
    role: str | None = None,
    label: str | None = None,
) -> RenderBlock:
    ref = resolve_image_ref(raw, json_file, image_root, sample)
    kind = "image" if ref.exists else "missing_image"
    return RenderBlock(
        kind=kind,
        json_path=json_path,
        schema_name=schema_name,
        value=raw,
        role=role,
        label=label,
        image=ref,
    )


def block_from_text(
    text_value: str,
    json_path: str,
    schema_name: str,
    role: str | None = None,
    label: str | None = None,
) -> RenderBlock:
    return RenderBlock(
        kind="text",
        json_path=json_path,
        schema_name=schema_name,
        value=text_value,
        role=role,
        label=label,
    )


def blocks_from_messages(sample: Any, json_file: Path, image_root: str) -> list[RenderBlock]:
    if not isinstance(sample, dict):
        return []
    messages = sample.get("messages")
    base_path = "messages"
    if not isinstance(messages, list):
        messages = sample.get("conversations")
        base_path = "conversations"
    if not isinstance(messages, list):
        return []

    blocks: list[RenderBlock] = []
    for msg_idx, message in enumerate(messages):
        role = None
        content = message
        msg_path = f"{base_path}[{msg_idx}]"
        if isinstance(message, dict):
            role = str(first_existing_key(message, ("role", "from", "speaker", "author")) or "")
            content = first_existing_key(message, ("content", "value", "text", "message"))

        if isinstance(content, list):
            for item_idx, item in enumerate(content):
                item_path = f"{msg_path}.content[{item_idx}]"
                blocks.extend(blocks_from_typed_item(item, item_path, json_file, image_root, sample, role or None))
        elif isinstance(content, str):
            if looks_like_image_string(content):
                blocks.append(block_from_image(content, f"{msg_path}.content", "image", json_file, image_root, sample, role or None))
            else:
                blocks.append(block_from_text(content, f"{msg_path}.content", "text", role or None))
        elif isinstance(content, dict):
            blocks.extend(blocks_from_typed_item(content, f"{msg_path}.content", json_file, image_root, sample, role or None))

    return blocks


def blocks_from_typed_item(
    item: Any,
    json_path: str,
    json_file: Path,
    image_root: str,
    sample: Any,
    role: str | None = None,
) -> list[RenderBlock]:
    if isinstance(item, str):
        if looks_like_image_string(item):
            return [block_from_image(item, json_path, "image", json_file, image_root, sample, role)]
        return [block_from_text(item, json_path, "text", role)]
    if not isinstance(item, dict):
        return []

    item_type = str(item.get("type", "")).lower()
    label = first_existing_key(item, ("label", "name", "title"))

    if item_type in {"image", "img", "picture", "photo"}:
        raw = first_existing_key(item, ("path", "url", "uri", "image", "image_path", "file", "filename", "file_name"))
        if isinstance(raw, str):
            return [
                block_from_image(
                    raw,
                    f"{json_path}.{guess_child_key(item, raw)}",
                    item_type or "image",
                    json_file,
                    image_root,
                    sample,
                    role,
                    str(label) if label is not None else None,
                )
            ]

    if item_type in {"text", "markdown", "caption"}:
        text_value = first_existing_key(item, ("text", "content", "value", "caption"))
        if isinstance(text_value, str):
            return [
                block_from_text(
                    text_value,
                    f"{json_path}.{guess_child_key(item, text_value)}",
                    item_type or "text",
                    role,
                    str(label) if label is not None else None,
                )
            ]

    raw = first_existing_key(item, ("path", "url", "uri", "image", "image_path", "file", "filename", "file_name"))
    if isinstance(raw, str) and (looks_like_image_string(raw) or key_suggests_image(guess_child_key(item, raw))):
        return [block_from_image(raw, f"{json_path}.{guess_child_key(item, raw)}", "image", json_file, image_root, sample, role)]

    text_value = first_existing_key(item, ("text", "caption", "prompt", "content", "value"))
    if isinstance(text_value, str) and (len(text_value.strip()) > 8 or key_suggests_text(guess_child_key(item, text_value))):
        return [block_from_text(text_value, f"{json_path}.{guess_child_key(item, text_value)}", "text", role)]

    return []


def guess_child_key(mapping: dict[str, Any], target: Any) -> str:
    for key, value in mapping.items():
        if value is target or value == target:
            return str(key)
    return "value"


def generic_blocks(sample: Any, json_file: Path, image_root: str, max_blocks: int = 160) -> list[RenderBlock]:
    blocks: list[RenderBlock] = []

    def walk(value: Any, path: str, parent_key: str | None = None, role: str | None = None, depth: int = 0) -> None:
        if len(blocks) >= max_blocks or depth > 12:
            return
        if isinstance(value, dict):
            typed = blocks_from_typed_item(value, path, json_file, image_root, sample, role)
            if typed:
                blocks.extend(typed)
                return
            next_role = role
            role_value = first_existing_key(value, ("role", "from", "speaker", "author"))
            if isinstance(role_value, str):
                next_role = role_value
            for key, child in value.items():
                walk(child, f"{path}.{key}", str(key), next_role, depth + 1)
        elif isinstance(value, list):
            for idx, child in enumerate(value):
                walk(child, f"{path}[{idx}]", parent_key, role, depth + 1)
        elif isinstance(value, str):
            if looks_like_image_string(value) or key_suggests_image(parent_key):
                if looks_like_image_string(value):
                    blocks.append(block_from_image(value, path, parent_key or "image", json_file, image_root, sample, role))
            elif key_suggests_text(parent_key) or len(value.strip()) >= 60:
                blocks.append(block_from_text(value, path, parent_key or "text", role))

    walk(sample, "$")
    return blocks


def build_render_blocks(sample: Any, json_file: Path, image_root: str) -> list[RenderBlock]:
    message_blocks = blocks_from_messages(sample, json_file, image_root)
    if message_blocks:
        return message_blocks
    return generic_blocks(sample, json_file, image_root)


def summarize_sample(sample: Any) -> list[tuple[str, str]]:
    if not isinstance(sample, dict):
        return [("type", type(sample).__name__)]
    preferred = ("id", "dataset", "task", "language", "domain", "sub_domain", "source_id")
    result: list[tuple[str, str]] = []
    for key in preferred:
        if key in sample and not isinstance(sample[key], (dict, list)):
            result.append((key, str(sample[key])))
    meta = sample.get("meta")
    if isinstance(meta, dict):
        for key in ("source_file", "source_num_samples", "source_num_images", "final_image_label"):
            if key in meta:
                result.append((f"meta.{key}", str(meta[key])))
    return result[:10]


def flatten_fields(value: Any, max_rows: int = 500) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []

    def walk(child: Any, path: str, depth: int = 0) -> None:
        if len(rows) >= max_rows or depth > 10:
            return
        if isinstance(child, dict):
            rows.append({"path": path, "type": "object", "preview": f"{len(child)} keys"})
            for key, item in child.items():
                walk(item, f"{path}.{key}", depth + 1)
        elif isinstance(child, list):
            rows.append({"path": path, "type": "array", "preview": f"{len(child)} items"})
            for idx, item in enumerate(child[:80]):
                walk(item, f"{path}[{idx}]", depth + 1)
            if len(child) > 80:
                rows.append({"path": f"{path}[...]", "type": "truncated", "preview": f"{len(child) - 80} more items"})
        else:
            rows.append({"path": path, "type": type(child).__name__, "preview": preview_value(child, 150)})

    walk(value, "$")
    return rows
