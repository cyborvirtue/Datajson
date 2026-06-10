from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import streamlit as st

from datajson.config import COLLECTION_KEYS
from datajson.models import DatasetInfo

try:
    import orjson
except ImportError:  # pragma: no cover - optional speedup
    orjson = None


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


def sample_count_from_info(info: DatasetInfo) -> int:
    return max(info.sample_count, 0)
