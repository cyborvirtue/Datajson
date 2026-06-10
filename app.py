from __future__ import annotations

import html
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import unquote, urlparse

import streamlit as st

try:
    import orjson
except ImportError:  # pragma: no cover - optional speedup
    orjson = None


APP_TITLE = "Datajson"
DEFAULT_JSONL = (
    "/Users/kalami/Keyan/dllm/Work01-data收集/datapipeline/"
    "01_格式转换/Weave/weave_interleaved_en.jsonl"
)

IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".tif", ".tiff")
IMAGE_KEYS = {
    "image",
    "images",
    "img",
    "imgs",
    "photo",
    "picture",
    "pic",
    "filepath",
    "file_path",
    "image_path",
    "img_path",
    "path",
    "url",
    "uri",
    "filename",
    "file_name",
}
TEXT_KEYS = {
    "text",
    "caption",
    "prompt",
    "instruction",
    "question",
    "answer",
    "response",
    "content",
    "value",
    "description",
    "query",
    "title",
}
COLLECTION_KEYS = {
    "data",
    "samples",
    "items",
    "records",
    "instances",
    "examples",
    "rows",
    "annotations",
    "dataset",
}


@dataclass
class DatasetInfo:
    format_name: str
    sample_count: int
    root: Any | None = None
    offsets: tuple[int, ...] = ()
    collection_path: str = "$"
    parse_note: str = ""


@dataclass
class ImageRef:
    raw: str
    exists: bool
    is_url: bool
    resolved: str | None
    status: str


@dataclass
class RenderBlock:
    kind: str
    json_path: str
    schema_name: str
    value: Any
    role: str | None = None
    label: str | None = None
    image: ImageRef | None = None


def loads_json(data: bytes | str) -> Any:
    if isinstance(data, str):
        data_bytes = data.encode("utf-8")
    else:
        data_bytes = data
    if orjson is not None:
        return orjson.loads(data_bytes)
    return json.loads(data_bytes.decode("utf-8"))


def dumps_json(value: Any, indent: int = 2) -> str:
    if orjson is not None:
        return orjson.dumps(value, option=orjson.OPT_INDENT_2).decode("utf-8")
    return json.dumps(value, indent=indent, ensure_ascii=False)


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


def infer_parser_mode(path: Path, selected: str) -> str:
    if selected != "auto":
        return selected
    suffix = path.suffix.lower()
    if suffix in {".jsonl", ".ndjson"}:
        return "jsonl"
    return "json"


@st.cache_data(show_spinner=False)
def file_stat(path_text: str) -> tuple[int, int]:
    path = Path(path_text).expanduser()
    stat = path.stat()
    return stat.st_size, stat.st_mtime_ns


@st.cache_data(show_spinner=False)
def build_jsonl_offsets(path_text: str, size: int, mtime_ns: int) -> tuple[int, ...]:
    del size, mtime_ns
    offsets: list[int] = []
    with Path(path_text).expanduser().open("rb") as handle:
        while True:
            pos = handle.tell()
            line = handle.readline()
            if not line:
                break
            if line.strip():
                offsets.append(pos)
    return tuple(offsets)


@st.cache_data(show_spinner=False)
def load_json_root(path_text: str, size: int, mtime_ns: int) -> Any:
    del size, mtime_ns
    return loads_json(Path(path_text).expanduser().read_bytes())


def read_jsonl_sample(path: Path, offsets: tuple[int, ...], index: int) -> Any:
    with path.open("rb") as handle:
        handle.seek(offsets[index])
        line = handle.readline()
    return loads_json(line)


def find_collection_candidates(root: Any, max_depth: int = 3) -> list[tuple[str, int, str]]:
    candidates: list[tuple[str, int, str]] = []

    def walk(value: Any, path: str, depth: int) -> None:
        if isinstance(value, list):
            if value:
                candidates.append((path, len(value), type(value[0]).__name__))
            else:
                candidates.append((path, 0, "empty"))
            return
        if isinstance(value, dict) and depth < max_depth:
            for key, child in value.items():
                if isinstance(child, list):
                    walk(child, f"{path}.{key}", depth + 1)
                elif isinstance(child, dict):
                    walk(child, f"{path}.{key}", depth + 1)

    if isinstance(root, list):
        candidates.append(("$", len(root), type(root[0]).__name__ if root else "empty"))
    elif isinstance(root, dict):
        for key, child in root.items():
            if isinstance(child, list) and key.lower() in COLLECTION_KEYS:
                walk(child, f"$.{key}", 1)
        for key, child in root.items():
            if isinstance(child, list) and key.lower() not in COLLECTION_KEYS:
                walk(child, f"$.{key}", 1)
            elif isinstance(child, dict):
                walk(child, f"$.{key}", 1)
    return candidates


def get_by_collection_path(root: Any, path: str) -> Any:
    if path == "$":
        return root
    current = root
    tokens = path[2:].split(".") if path.startswith("$.") else path.split(".")
    for token in tokens:
        if not token:
            continue
        if isinstance(current, dict):
            current = current[token]
        elif isinstance(current, list):
            current = current[int(token)]
        else:
            raise KeyError(path)
    return current


def choose_auto_collection_path(root: Any) -> str:
    if isinstance(root, list):
        return "$"
    if not isinstance(root, dict):
        return "$"
    for key, value in root.items():
        if key.lower() in COLLECTION_KEYS and isinstance(value, list):
            return f"$.{key}"
    return "$"


def get_json_sample(root: Any, collection_path: str, index: int) -> tuple[Any, int]:
    collection = get_by_collection_path(root, collection_path)
    if isinstance(collection, list):
        if not collection:
            return None, 0
        return collection[index], len(collection)
    return collection, 1


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


def sample_count_from_info(info: DatasetInfo) -> int:
    return max(info.sample_count, 0)


def svg_icon(name: str, size: int = 18) -> str:
    icons = {
        "database": '<path d="M4 6c0-1.7 3.6-3 8-3s8 1.3 8 3-3.6 3-8 3-8-1.3-8-3Z"/><path d="M4 6v6c0 1.7 3.6 3 8 3s8-1.3 8-3V6"/><path d="M4 12v6c0 1.7 3.6 3 8 3s8-1.3 8-3v-6"/>',
        "image": '<rect x="3" y="5" width="18" height="14" rx="3"/><circle cx="8" cy="10" r="1.5"/><path d="m5 17 5-5 4 4 2-2 3 3"/>',
        "text": '<path d="M5 6h14"/><path d="M5 10h10"/><path d="M5 14h14"/><path d="M5 18h8"/>',
        "missing": '<rect x="4" y="4" width="16" height="16" rx="3"/><path d="m7 17 10-10"/><path d="m8 8 8 8"/>',
        "anchor": '<path d="M12 4v16"/><path d="M8 8h8"/><path d="M7 16c1 2.7 3.2 4 5 4s4-1.3 5-4"/><circle cx="12" cy="4" r="2"/>',
        "settings": '<path d="M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V22a2 2 0 1 1-4 0v-.2a1.7 1.7 0 0 0-1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.2a1.7 1.7 0 0 0 1.5-1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3h.1a1.7 1.7 0 0 0 1-1.5V2a2 2 0 1 1 4 0v.2a1.7 1.7 0 0 0 1 1.5h.1a1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8v.1a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.2a1.7 1.7 0 0 0-1.4 1Z"/>',
        "download": '<path d="M12 3v12"/><path d="m7 10 5 5 5-5"/><path d="M5 21h14"/>',
    }
    body = icons.get(name, icons["database"])
    return (
        f'<svg class="ui-icon" width="{size}" height="{size}" viewBox="0 0 24 24" '
        f'fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" '
        f'stroke-linejoin="round" aria-hidden="true">{body}</svg>'
    )


def install_css(theme: str) -> None:
    if theme == "light":
        theme_vars = {
            "scheme": "light",
            "bg": "#ffffff",
            "panel": "#ffffff",
            "panel2": "#f7f2ff",
            "line": "rgba(88, 65, 140, .16)",
            "line_strong": "rgba(88, 65, 140, .25)",
            "text": "#171422",
            "muted": "#6f6680",
            "cyan": "#7c3aed",
            "green": "#0d9488",
            "amber": "#b7791f",
            "coral": "#dc4c64",
            "app_bg": "radial-gradient(circle at 14% 6%, rgba(124,58,237,.12), transparent 27%), radial-gradient(circle at 86% 12%, rgba(196,181,253,.20), transparent 25%), linear-gradient(135deg, #ffffff 0%, #fbfaff 52%, #f3edff 100%)",
            "sidebar_bg": "rgba(255, 255, 255, .96)",
            "topbar_bg": "rgba(255, 255, 255, .90)",
            "card_bg": "rgba(124, 58, 237, .045)",
            "card_bg_strong": "rgba(255, 255, 255, .78)",
            "path_bg": "rgba(124, 58, 237, .055)",
            "path_text": "#453b5f",
            "chip_text": "#453b5f",
            "text_body": "#242031",
            "code_text": "#4c4564",
            "shadow": "0 22px 58px rgba(74, 48, 126, .12)",
            "missing_bg": "rgba(220, 76, 100, .055)",
            "input_bg": "rgba(255, 255, 255, .86)",
            "container_bg": "rgba(255,255,255,.72)",
        }
    else:
        theme_vars = {
            "scheme": "dark",
            "bg": "#080b0f",
            "panel": "#11161b",
            "panel2": "#171d23",
            "line": "rgba(255,255,255,.10)",
            "line_strong": "rgba(255,255,255,.18)",
            "text": "#edf2f4",
            "muted": "#8e9aa5",
            "cyan": "#53d7e8",
            "green": "#72e3a1",
            "amber": "#f2c46d",
            "coral": "#ff7b6f",
            "app_bg": "radial-gradient(circle at 12% 8%, rgba(83,215,232,.14), transparent 28%), radial-gradient(circle at 86% 12%, rgba(242,196,109,.09), transparent 24%), linear-gradient(135deg, #080a0d 0%, #11161b 48%, #090d11 100%)",
            "sidebar_bg": "rgba(12, 16, 20, .94)",
            "topbar_bg": "rgba(15, 19, 23, .88)",
            "card_bg": "rgba(255,255,255,.045)",
            "card_bg_strong": "rgba(15,19,23,.72)",
            "path_bg": "rgba(255,255,255,.035)",
            "path_text": "#cdd7dc",
            "chip_text": "#c7d0d6",
            "text_body": "#e6ecef",
            "code_text": "#d8e5e9",
            "shadow": "0 24px 70px rgba(0,0,0,.28)",
            "missing_bg": "rgba(255,123,111,.06)",
            "input_bg": "rgba(255,255,255,.045)",
            "container_bg": "rgba(15,19,23,.72)",
        }

    css = """
<style>
:root {
  color-scheme: __scheme__;
  --bg: __bg__;
  --panel: __panel__;
  --panel-2: __panel2__;
  --line: __line__;
  --line-strong: __line_strong__;
  --text: __text__;
  --muted: __muted__;
  --cyan: __cyan__;
  --green: __green__;
  --amber: __amber__;
  --coral: __coral__;
  --app-bg: __app_bg__;
  --sidebar-bg: __sidebar_bg__;
  --topbar-bg: __topbar_bg__;
  --card-bg: __card_bg__;
  --card-bg-strong: __card_bg_strong__;
  --path-bg: __path_bg__;
  --path-text: __path_text__;
  --chip-text: __chip_text__;
  --text-body: __text_body__;
  --code-text: __code_text__;
  --app-shadow: __shadow__;
  --missing-bg: __missing_bg__;
  --input-bg: __input_bg__;
  --container-bg: __container_bg__;
}
.stApp {
  background: var(--app-bg);
  color: var(--text);
}
[data-testid="stHeader"] {
  background: transparent;
}
[data-testid="stSidebar"] {
  background: var(--sidebar-bg);
  border-right: 1px solid var(--line);
}
.block-container {
  max-width: none;
  padding-top: 1.2rem;
  padding-bottom: 3rem;
}
h1, h2, h3 {
  letter-spacing: 0;
}
code {
  color: var(--code-text);
}
.ui-icon {
  display: block;
}
.sidebar-title {
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 4px 0 18px;
  color: var(--text);
  font-size: 20px;
  font-weight: 760;
}
.sidebar-title .ui-icon {
  color: var(--cyan);
}
.app-topbar {
  border: 1px solid var(--line-strong);
  background: var(--topbar-bg);
  border-radius: 12px;
  padding: 16px 18px;
  margin-bottom: 18px;
  box-shadow: var(--app-shadow);
  backdrop-filter: blur(18px);
}
.app-title {
  display: flex;
  gap: 12px;
  align-items: center;
  font-weight: 720;
  font-size: 18px;
}
.brand-mark {
  width: 36px;
  height: 36px;
  display: inline-grid;
  place-items: center;
  border-radius: 10px;
  background: linear-gradient(135deg, color-mix(in srgb, var(--cyan) 22%, transparent), color-mix(in srgb, var(--green) 15%, transparent));
  border: 1px solid color-mix(in srgb, var(--cyan) 45%, transparent);
  color: var(--cyan);
}
.brand-mark .ui-icon {
  width: 20px;
  height: 20px;
}
.path-line {
  margin-top: 10px;
  padding: 10px 12px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--path-bg);
  color: var(--path-text);
  font-family: SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 12px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.metric-row {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
  margin-bottom: 16px;
}
.metric-card {
  border: 1px solid var(--line);
  border-radius: 10px;
  padding: 13px 14px;
  background: var(--card-bg);
}
.metric-card span {
  color: var(--muted);
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
}
.metric-card strong {
  display: block;
  margin-top: 5px;
  font-size: 20px;
}
.sample-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin: 8px 0 18px;
}
.meta-chip {
  border: 1px solid var(--line);
  border-radius: 999px;
  padding: 6px 9px;
  background: var(--card-bg);
  color: var(--chip-text);
  font-size: 12px;
}
.meta-chip b {
  color: var(--muted);
  font-weight: 700;
}
.block-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  border-bottom: 1px solid var(--line);
  padding-bottom: 10px;
  margin-bottom: 14px;
}
.block-title {
  display: flex;
  align-items: center;
  gap: 9px;
  min-width: 0;
}
.kind-badge {
  width: 26px;
  height: 26px;
  display: inline-grid;
  place-items: center;
  border-radius: 8px;
  border: 1px solid color-mix(in srgb, var(--cyan) 42%, transparent);
  color: var(--cyan);
  background: color-mix(in srgb, var(--cyan) 9%, transparent);
  font-size: 12px;
  font-weight: 800;
}
.kind-badge .ui-icon {
  width: 15px;
  height: 15px;
}
.kind-badge.missing {
  border-color: color-mix(in srgb, var(--coral) 45%, transparent);
  color: var(--coral);
  background: color-mix(in srgb, var(--coral) 9%, transparent);
}
.block-title strong {
  font-size: 13px;
  letter-spacing: .05em;
  text-transform: uppercase;
}
.role-pill {
  border: 1px solid var(--line-strong);
  border-radius: 999px;
  padding: 4px 8px;
  color: var(--chip-text);
  background: var(--card-bg);
  font-size: 11px;
}
.json-path {
  color: var(--muted);
  font-family: SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 11px;
  text-align: right;
  word-break: break-all;
}
.text-body {
  color: var(--text-body);
  font-size: 16px;
  line-height: 1.75;
  white-space: pre-wrap;
}
.image-frame {
  width: fit-content;
  max-width: 100%;
}
.image-frame img {
  border-radius: 10px;
  border: 1px solid var(--line);
}
.image-note {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  margin-top: 10px;
  color: var(--muted);
  font-family: SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 12px;
}
.status-pill {
  border-radius: 999px;
  padding: 4px 9px;
  font-family: Inter, system-ui, sans-serif;
  font-size: 11px;
  font-weight: 750;
}
.status-loaded {
  border: 1px solid rgba(114,227,161,.45);
  color: var(--green);
  background: rgba(114,227,161,.09);
}
.status-missing {
  border: 1px solid rgba(255,123,111,.45);
  color: var(--coral);
  background: rgba(255,123,111,.09);
}
.missing-box {
  min-height: 230px;
  display: grid;
  place-items: center;
  border: 1px dashed rgba(255,123,111,.45);
  border-radius: 12px;
  background:
    repeating-linear-gradient(135deg, rgba(255,255,255,.035) 0 10px, transparent 10px 22px),
    var(--missing-bg);
}
.missing-inner {
  text-align: center;
  max-width: 620px;
  padding: 22px;
}
.missing-icon {
  width: 72px;
  height: 72px;
  margin: 0 auto 14px;
  border: 2px solid rgba(255,123,111,.72);
  border-radius: 18px;
  position: relative;
}
.missing-icon:before,
.missing-icon:after {
  content: "";
  position: absolute;
  top: 33px;
  left: 13px;
  width: 46px;
  height: 3px;
  background: rgba(255,123,111,.88);
}
.missing-icon:before {
  transform: rotate(45deg);
}
.missing-icon:after {
  transform: rotate(-45deg);
}
.missing-inner strong {
  color: var(--coral);
  font-size: 16px;
}
.missing-inner code {
  display: block;
  margin-top: 10px;
  color: var(--code-text);
  white-space: normal;
  word-break: break-all;
}
.anchor-card {
  border: 1px solid var(--line);
  border-radius: 10px;
  background: var(--card-bg);
  padding: 11px 12px;
  margin-bottom: 9px;
}
.anchor-card b {
  display: block;
  font-size: 13px;
}
.anchor-card code {
  display: block;
  margin-top: 4px;
  color: var(--muted);
  font-size: 10px;
  white-space: normal;
}
.anchor-dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 999px;
  margin-right: 7px;
  background: var(--green);
}
.anchor-dot.missing {
  background: var(--coral);
}
.small-muted {
  color: var(--muted);
  font-size: 12px;
}
div[data-testid="stVerticalBlockBorderWrapper"] {
  border-color: rgba(255,255,255,.12);
  background: var(--container-bg);
}
.stTextInput input,
.stNumberInput input,
.stSelectbox div[data-baseweb="select"] > div {
  background: var(--input-bg);
  color: var(--text);
  border-color: var(--line);
}
.stButton button,
.stDownloadButton button {
  border-radius: 8px;
  border-color: var(--line-strong);
}
.stButton button[kind="primary"] {
  background: var(--cyan);
  border-color: var(--cyan);
  color: white;
}
</style>
        """
    for key, value in theme_vars.items():
        css = css.replace(f"__{key}__", value)
    st.markdown(css, unsafe_allow_html=True)


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


def create_dataset_info(path: Path, parser_mode: str, collection_path: str | None = None) -> DatasetInfo:
    size, mtime_ns = file_stat(str(path))
    mode = infer_parser_mode(path, parser_mode)
    if mode == "jsonl":
        offsets = build_jsonl_offsets(str(path), size, mtime_ns)
        return DatasetInfo(format_name="jsonl", sample_count=len(offsets), offsets=offsets)

    root = load_json_root(str(path), size, mtime_ns)
    chosen_path = collection_path or choose_auto_collection_path(root)
    _, sample_count = get_json_sample(root, chosen_path, 0)
    return DatasetInfo(format_name="json", sample_count=sample_count, root=root, collection_path=chosen_path)


def load_current_sample(path: Path, info: DatasetInfo, index: int) -> Any:
    if info.format_name == "jsonl":
        return read_jsonl_sample(path, info.offsets, index)
    sample, _ = get_json_sample(info.root, info.collection_path, index)
    return sample


def sync_index(sample_count: int) -> int:
    if "sample_index" not in st.session_state:
        st.session_state.sample_index = 0
    if sample_count <= 0:
        st.session_state.sample_index = 0
    else:
        st.session_state.sample_index = min(max(int(st.session_state.sample_index), 0), sample_count - 1)
    return st.session_state.sample_index


def clamp_index(index: Any, sample_count: int) -> int:
    if sample_count <= 0:
        return 0
    try:
        numeric = int(index)
    except (TypeError, ValueError):
        numeric = 0
    return min(max(numeric, 0), sample_count - 1)


def commit_sample_index(sample_count: int) -> None:
    st.session_state.sample_index = clamp_index(st.session_state.get("sample_index_input", 0), sample_count)
    st.session_state.sample_index_input = st.session_state.sample_index


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
