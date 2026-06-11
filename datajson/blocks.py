from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import unquote, urlparse

from datajson.config import IMAGE_EXTS, IMAGE_KEYS, TEXT_KEYS
from datajson.json_store import dumps_json
from datajson.models import ImageRef, RenderBlock

IMAGE_LABEL_RE = re.compile(r"\bImage\s*#\s*(\d+)\b", re.IGNORECASE)
INDEXED_IMAGE_RE = re.compile(r"(?<![\w/.-])(?:image|img|pic|picture|photo)[\s_#:-]*(\d+)(?![\w/.-])", re.IGNORECASE)
CHINESE_IMAGE_LABEL_RE = re.compile(r"(?:图片|图像|影像)\s*[#:_-]?\s*(\d+)")
PLAIN_IMAGE_PLACEHOLDER_RE = re.compile(r"<\s*(?:image|img|pic|picture|photo)\s*/?\s*>|\[\s*(?:image|img|pic|picture|photo)\s*\]", re.IGNORECASE)
INDEXED_IMAGE_PLACEHOLDER_RE = re.compile(
    r"<\s*(?:image|img|pic|picture|photo)[\s_#:-]*(\d+)\s*/?\s*>|"
    r"\[\s*(?:image|img|pic|picture|photo)[\s_#:-]*(\d+)\s*\]",
    re.IGNORECASE,
)
MARKDOWN_IMAGE_RE = re.compile(r"!\[([^\]]*)\]\(([^)\s]+)(?:\s+[\"'][^\"']*[\"'])?\)")
HTML_IMAGE_RE = re.compile(r"<img\b[^>]*\bsrc=[\"']([^\"']+)[\"'][^>]*>", re.IGNORECASE)

IMAGE_RECORD_KEYS = (
    "data_url",
    "data_uri",
    "image_url",
    "image_uri",
    "bytes",
    "path",
    "local_path",
    "relative_path",
    "url",
    "uri",
    "src",
    "source",
    "image",
    "img",
    "image_path",
    "img_path",
    "content",
    "file",
    "filepath",
    "file_path",
    "filename",
    "file_name",
    "image_file",
    "image_filename",
    "original_path",
    "asset",
    "asset_path",
    "media",
    "media_path",
)
IMAGE_COLLECTION_KEYS = (
    "image",
    "images",
    "img",
    "imgs",
    "image_list",
    "image_paths",
    "image_urls",
    "image_url",
    "original_image",
    "original_images",
    "source_image",
    "source_images",
    "input_image",
    "input_images",
    "pictures",
    "photos",
    "media",
    "assets",
)
TEXT_RECORD_KEYS = (
    "text",
    "content",
    "value",
    "caption",
    "prompt",
    "instruction",
    "question",
    "answer",
    "response",
    "input",
    "output",
    "query",
    "query_text",
    "answer_text",
    "ocr",
    "ground_truth",
)
IMAGE_TYPE_NAMES = {
    "image",
    "img",
    "picture",
    "photo",
    "input_image",
    "image_url",
    "input_image_url",
    "local_image",
}
TEXT_TYPE_NAMES = {"text", "markdown", "caption", "input_text", "output_text"}


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


def type_suggests_image(item_type: str | None) -> bool:
    if not item_type:
        return False
    normalized = item_type.lower().replace("-", "_")
    return normalized in IMAGE_TYPE_NAMES or normalized.endswith("_image") or normalized.endswith("_image_url")


def type_suggests_text(item_type: str | None) -> bool:
    if not item_type:
        return False
    normalized = item_type.lower().replace("-", "_")
    return normalized in TEXT_TYPE_NAMES or normalized.endswith("_text")


def first_existing_item(value: dict[str, Any], keys: Iterable[str]) -> tuple[str, Any] | None:
    for key in keys:
        if key in value and value[key] not in (None, ""):
            return key, value[key]
    lower_map = {str(key).lower(): key for key in value.keys()}
    for key in keys:
        actual = lower_map.get(key.lower())
        if actual is not None and value[actual] not in (None, ""):
            return str(actual), value[actual]
    return None


def value_is_usable_image_ref(value: str, key: str | None = None) -> bool:
    text = normalize_path_text(value)
    if not text:
        return False
    if looks_like_image_string(text) or is_url(text):
        return True
    if key and key.lower() in {"data", "base64", "bytes"}:
        return False
    if key_suggests_image(key) and len(text) <= 2048 and "\n" not in text:
        return True
    return False


def discover_sample_image_dirs(sample: Any) -> list[str]:
    keys = {
        "source_image_dir",
        "image_dir",
        "images_dir",
        "img_dir",
        "image_root",
        "root",
        "media_dir",
        "asset_dir",
        "assets_dir",
        "data_dir",
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


def canonical_image_label(value: str | None) -> str | None:
    number = image_reference_number(value)
    if number is None:
        return None
    return f"Image #{number}"


def image_reference_number(value: str | None) -> int | None:
    if not value:
        return None
    text = value.strip()
    for regex in (IMAGE_LABEL_RE, INDEXED_IMAGE_PLACEHOLDER_RE, INDEXED_IMAGE_RE, CHINESE_IMAGE_LABEL_RE):
        match = regex.search(text)
        if not match:
            continue
        for group in match.groups():
            if group is not None:
                return int(group)
    return None


def image_reference_labels(value: str) -> list[str]:
    raw = value.strip()
    labels = [raw]
    canonical = canonical_image_label(raw)
    if canonical is not None:
        labels.append(canonical)
    number = image_reference_number(raw)
    if number is not None:
        labels.extend((f"image_{number}", f"img_{number}", f"image{number}", f"img{number}", f"图片{number}", f"图像{number}"))

    unique: list[str] = []
    seen: set[str] = set()
    for label in labels:
        if label and label not in seen:
            seen.add(label)
            unique.append(label)
    return unique


def image_value_from_source_dict(source: dict[str, Any]) -> str | None:
    direct = image_value_from_record(source)
    if direct is not None:
        return direct
    media_type = first_existing_key(source, ("media_type", "mime_type", "mime", "content_type"))
    data = first_existing_key(source, ("data", "base64", "bytes"))
    if isinstance(data, str) and data.startswith("data:image/"):
        return data
    if isinstance(media_type, str) and media_type.startswith("image/") and isinstance(data, str) and data.strip():
        return f"data:{media_type};base64,{data.strip()}"
    return None


def image_value_from_record(record: Any) -> str | None:
    if isinstance(record, str) and value_is_usable_image_ref(record):
        return record
    if not isinstance(record, dict):
        return None

    nested = first_existing_key(record, ("image_url", "image", "source", "asset", "media"))
    if isinstance(nested, dict):
        nested_value = image_value_from_source_dict(nested)
        if nested_value is not None:
            return nested_value

    item = first_existing_item(record, IMAGE_RECORD_KEYS)
    if item is None:
        return None
    key, value = item
    if isinstance(value, dict):
        return image_value_from_source_dict(value)
    if isinstance(value, str) and value_is_usable_image_ref(value, key):
        return value
    return None


def image_record_label(record: Any, fallback: str | None = None) -> str | None:
    if isinstance(record, dict):
        label = first_existing_key(record, ("label", "name", "title", "id", "image_id", "content"))
        if isinstance(label, (str, int)):
            return str(label)
    return fallback


def image_record_matches_label(record: Any, label: str) -> bool:
    record_label = image_record_label(record)
    if record_label is None:
        return False
    record_canonical = canonical_image_label(record_label)
    label_canonical = canonical_image_label(label)
    return record_label.strip() == label or (record_canonical is not None and record_canonical == label_canonical)


def image_value_from_collection(collection: Any, label: str) -> str | None:
    if isinstance(collection, dict):
        direct = collection.get(label)
        value = image_value_from_record(direct)
        if value is None and isinstance(direct, str) and value_is_usable_image_ref(direct, label):
            value = direct
        if value is not None:
            return value
        for key, record in collection.items():
            if str(key).strip() == label or canonical_image_label(str(key)) == label or image_record_matches_label(record, label):
                value = image_value_from_record(record)
                if value is None and isinstance(record, str) and value_is_usable_image_ref(record, str(key)):
                    value = record
                if value is not None:
                    return value
    elif isinstance(collection, list):
        for record in collection:
            if image_record_matches_label(record, label):
                value = image_value_from_record(record)
                if value is not None:
                    return value
    return None


def iter_sample_image_collections(sample: dict[str, Any]) -> list[tuple[str, Any]]:
    collections: list[tuple[str, Any]] = []

    def add_from(mapping: dict[str, Any], prefix: str = "") -> None:
        lower_map = {str(key).lower(): key for key in mapping.keys()}
        for key in IMAGE_COLLECTION_KEYS:
            actual = lower_map.get(key.lower())
            if actual is not None and mapping[actual] not in (None, ""):
                collections.append((f"{prefix}{actual}", mapping[actual]))

    add_from(sample)
    meta = sample.get("meta")
    if isinstance(meta, dict):
        add_from(meta, "meta.")
    return collections


def sample_image_candidates(sample: Any) -> list[tuple[str | None, str]]:
    if not isinstance(sample, dict):
        return []

    candidates: list[tuple[str | None, str]] = []
    seen: set[tuple[str | None, str]] = set()

    def add(label: str | None, raw: str | None) -> None:
        if raw is None:
            return
        marker = (label, raw)
        if marker in seen:
            return
        seen.add(marker)
        candidates.append(marker)

    for collection_name, collection in iter_sample_image_collections(sample):
        if isinstance(collection, (str, dict)):
            raw = image_value_from_record(collection)
            if raw is None and isinstance(collection, str) and value_is_usable_image_ref(collection, collection_name):
                raw = collection
            add(image_record_label(collection, collection_name), raw)
        if isinstance(collection, dict):
            for key, record in collection.items():
                raw = image_value_from_record(record)
                if raw is None and isinstance(record, str) and value_is_usable_image_ref(record, str(key)):
                    raw = record
                add(image_record_label(record, str(key)), raw)
        elif isinstance(collection, list):
            for idx, record in enumerate(collection):
                raw = image_value_from_record(record)
                if raw is None and isinstance(record, str) and value_is_usable_image_ref(record, collection_name):
                    raw = record
                add(image_record_label(record, f"Image #{idx + 1}"), raw)

    return candidates


def candidate_matches_label(candidate_label: str | None, label: str) -> bool:
    if not candidate_label:
        return False
    candidate_canonical = canonical_image_label(candidate_label)
    label_canonical = canonical_image_label(label)
    return candidate_label.strip() == label or (candidate_canonical is not None and candidate_canonical == label_canonical)


def resolve_sample_image_reference(raw: str, sample: Any) -> str | None:
    if not isinstance(sample, dict):
        return None

    raw_text = normalize_path_text(raw)
    if looks_like_image_string(raw_text) or is_url(raw_text) or raw_text.startswith("data:image/"):
        return None

    labels = image_reference_labels(raw_text)
    for label in labels:
        target = sample.get(label)
        value = image_value_from_record(target)
        if value is None and isinstance(target, str) and value_is_usable_image_ref(target, label):
            value = target
        if value is not None:
            return value

    meta = sample.get("meta") if isinstance(sample.get("meta"), dict) else {}
    for collection in (
        sample.get("images"),
        sample.get("original_images"),
        sample.get("image_list"),
        sample.get("image_paths"),
        sample.get("image_urls"),
        sample.get("input_images"),
        sample.get("source_images"),
        sample.get("assets"),
        sample.get("media"),
        meta.get("images") if isinstance(meta, dict) else None,
        meta.get("original_images") if isinstance(meta, dict) else None,
        meta.get("image_paths") if isinstance(meta, dict) else None,
        meta.get("image_urls") if isinstance(meta, dict) else None,
    ):
        for label in labels:
            value = image_value_from_collection(collection, label)
            if value is not None:
                return value

    candidates = sample_image_candidates(sample)
    for label in labels:
        for candidate_label, raw_value in candidates:
            if candidate_matches_label(candidate_label, label):
                return raw_value

    number = image_reference_number(raw_text)
    if number is not None and candidates:
        ordered_indices = [number - 1] if number > 0 else []
        ordered_indices.append(number)
        for idx in ordered_indices:
            if 0 <= idx < len(candidates):
                return candidates[idx][1]
    return None


def find_sample_image_references(text: str, sample: Any) -> list[tuple[str, str]]:
    refs: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()

    def add(label: str, raw: str | None) -> None:
        if raw is None:
            return
        marker = (label, raw)
        if marker in seen:
            return
        refs.append(marker)
        seen.add(marker)

    for alt, raw in MARKDOWN_IMAGE_RE.findall(text):
        label = alt.strip() or "markdown image"
        add(label, raw.strip("<>\"'"))

    for raw in HTML_IMAGE_RE.findall(text):
        add("html image", raw.strip())

    for regex in (IMAGE_LABEL_RE, INDEXED_IMAGE_PLACEHOLDER_RE, INDEXED_IMAGE_RE, CHINESE_IMAGE_LABEL_RE):
        for match in regex.finditer(text):
            token = match.group(0)
            label = canonical_image_label(token) or token.strip()
            add(label, resolve_sample_image_reference(token, sample))

    candidates = sample_image_candidates(sample)
    candidate_idx = 0
    for match in PLAIN_IMAGE_PLACEHOLDER_RE.finditer(text):
        while candidate_idx < len(candidates) and any(raw == candidates[candidate_idx][1] for _, raw in seen):
            candidate_idx += 1
        if candidate_idx >= len(candidates):
            break
        label, raw = candidates[candidate_idx]
        add(label or "image placeholder", raw)
        candidate_idx += 1
    return refs


def remember_rendered_image_labels(blocks: Iterable[RenderBlock], rendered_labels: set[str]) -> None:
    for block in blocks:
        if block.kind not in {"image", "missing_image"}:
            continue
        label = canonical_image_label(block.label) or block.label
        if label is not None:
            rendered_labels.add(label)
        if block.image is not None:
            rendered_labels.add(f"raw:{normalize_path_text(block.image.raw)}")


def image_reference_marker(label: str, raw: str) -> str:
    return canonical_image_label(label) or f"raw:{normalize_path_text(raw)}"


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


def blocks_from_text_references(
    text: str,
    json_path: str,
    json_file: Path,
    image_root: str,
    sample: Any,
    role: str | None = None,
    rendered_image_labels: set[str] | None = None,
) -> list[RenderBlock]:
    blocks: list[RenderBlock] = []
    for label, raw in find_sample_image_references(text, sample):
        marker = image_reference_marker(label, raw)
        raw_marker = f"raw:{normalize_path_text(raw)}"
        if rendered_image_labels is not None and (marker in rendered_image_labels or raw_marker in rendered_image_labels):
            continue
        new_block = block_from_image(raw, f"{json_path}.{label}", "image", json_file, image_root, sample, role, label)
        blocks.append(new_block)
        if rendered_image_labels is not None:
            remember_rendered_image_labels([new_block], rendered_image_labels)
    return blocks


def blocks_from_messages(sample: Any, json_file: Path, image_root: str) -> list[RenderBlock]:
    if not isinstance(sample, dict):
        return []
    messages = sample.get("messages")
    base_path = "messages"
    if not isinstance(messages, list):
        messages = sample.get("conversations")
        base_path = "conversations"
    if not isinstance(messages, list):
        messages = sample.get("chats")
        base_path = "chats"
    if not isinstance(messages, list):
        return []

    blocks: list[RenderBlock] = []
    rendered_image_labels: set[str] = set()
    for msg_idx, message in enumerate(messages):
        role = None
        content = message
        msg_path = f"{base_path}[{msg_idx}]"
        item_type = ""
        if isinstance(message, dict):
            role = str(first_existing_key(message, ("role", "from", "speaker", "author")) or "")
            item_type = str(message.get("type", "")).lower()
            content = first_existing_key(message, ("content", "value", "text", "message", "parts", "contents"))

        if isinstance(content, list):
            for item_idx, item in enumerate(content):
                item_path = f"{msg_path}.content[{item_idx}]"
                new_blocks = blocks_from_typed_item(item, item_path, json_file, image_root, sample, role or None)
                blocks.extend(new_blocks)
                remember_rendered_image_labels(new_blocks, rendered_image_labels)
        elif isinstance(content, str):
            referenced_image = resolve_sample_image_reference(content, sample)
            if looks_like_image_string(content) or (
                type_suggests_image(item_type) and (referenced_image is not None or value_is_usable_image_ref(content, "image"))
            ):
                new_blocks = [
                    block_from_image(
                        referenced_image or content,
                        f"{msg_path}.content",
                        "image",
                        json_file,
                        image_root,
                        sample,
                        role or None,
                        content if referenced_image else None,
                    )
                ]
                blocks.extend(new_blocks)
                remember_rendered_image_labels(new_blocks, rendered_image_labels)
            else:
                blocks.extend(
                    blocks_from_text_references(
                        content,
                        f"{msg_path}.content",
                        json_file,
                        image_root,
                        sample,
                        role or None,
                        rendered_image_labels,
                    )
                )
                blocks.append(block_from_text(content, f"{msg_path}.content", "text", role or None))
        elif isinstance(content, dict):
            new_blocks = blocks_from_typed_item(content, f"{msg_path}.content", json_file, image_root, sample, role or None)
            blocks.extend(new_blocks)
            remember_rendered_image_labels(new_blocks, rendered_image_labels)

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
        reference_blocks = blocks_from_text_references(item, json_path, json_file, image_root, sample, role)
        return [*reference_blocks, block_from_text(item, json_path, "text", role)]
    if not isinstance(item, dict):
        return []

    item_type = str(item.get("type", "")).lower()
    label = first_existing_key(item, ("label", "name", "title"))

    if type_suggests_image(item_type):
        raw = image_value_from_record(item)
        if raw is None:
            raw = first_existing_key(item, IMAGE_RECORD_KEYS)
        if isinstance(raw, str):
            referenced_image = resolve_sample_image_reference(raw, sample)
            return [
                block_from_image(
                    referenced_image or raw,
                    f"{json_path}.{guess_child_key(item, raw)}",
                    item_type or "image",
                    json_file,
                    image_root,
                    sample,
                    role,
                    str(label) if label is not None else (raw if referenced_image else None),
                )
            ]

    if type_suggests_text(item_type):
        text_value = first_existing_key(item, TEXT_RECORD_KEYS)
        if isinstance(text_value, str):
            reference_blocks = blocks_from_text_references(text_value, f"{json_path}.{guess_child_key(item, text_value)}", json_file, image_root, sample, role)
            return [
                *reference_blocks,
                block_from_text(
                    text_value,
                    f"{json_path}.{guess_child_key(item, text_value)}",
                    item_type or "text",
                    role,
                    str(label) if label is not None else None,
                )
            ]

    image_item = first_existing_item(item, IMAGE_RECORD_KEYS)
    if image_item is not None:
        key, raw_value = image_item
        raw = image_value_from_record(item)
        if raw is None and isinstance(raw_value, dict):
            raw = image_value_from_source_dict(raw_value)
        if raw is None and isinstance(raw_value, str) and value_is_usable_image_ref(raw_value, key):
            raw = raw_value
        if isinstance(raw, str):
            referenced_image = resolve_sample_image_reference(raw, sample)
            return [block_from_image(referenced_image or raw, f"{json_path}.{key}", "image", json_file, image_root, sample, role)]

    text_value = first_existing_key(item, TEXT_RECORD_KEYS)
    if isinstance(text_value, str) and (len(text_value.strip()) > 8 or key_suggests_text(guess_child_key(item, text_value))):
        reference_blocks = blocks_from_text_references(text_value, f"{json_path}.{guess_child_key(item, text_value)}", json_file, image_root, sample, role)
        return [*reference_blocks, block_from_text(text_value, f"{json_path}.{guess_child_key(item, text_value)}", "text", role)]

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
            rendered_media = False
            if looks_like_image_string(value):
                blocks.append(block_from_image(value, path, parent_key or "image", json_file, image_root, sample, role))
                rendered_media = True
            elif key_suggests_image(parent_key) and value_is_usable_image_ref(value, parent_key):
                referenced_image = resolve_sample_image_reference(value, sample)
                blocks.append(block_from_image(referenced_image or value, path, parent_key or "image", json_file, image_root, sample, role))
                rendered_media = True
            else:
                blocks.extend(blocks_from_text_references(value, path, json_file, image_root, sample, role))
            if not rendered_media and (key_suggests_text(parent_key) or len(value.strip()) >= 60):
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
