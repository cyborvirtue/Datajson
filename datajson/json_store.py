from __future__ import annotations

import base64
import json
from datetime import date, datetime, time
from decimal import Decimal
from pathlib import Path
from typing import Any

import streamlit as st

from datajson.config import COLLECTION_KEYS
from datajson.models import DatasetInfo, ParquetFileInfo

try:
    import orjson
except ImportError:  # pragma: no cover - optional speedup
    orjson = None


def load_pyarrow_parquet() -> Any:
    try:
        import pyarrow.parquet as pq
    except ImportError as exc:  # pragma: no cover - dependency guidance
        raise RuntimeError("Parquet support requires pyarrow. Install it with `pip install pyarrow`.") from exc
    return pq


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
    if suffix == ".parquet" or path.is_dir():
        return "parquet"
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


def image_mime_from_bytes(data: bytes) -> str | None:
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith((b"GIF87a", b"GIF89a")):
        return "image/gif"
    if data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return "image/webp"
    if data.startswith(b"BM"):
        return "image/bmp"
    if data.startswith((b"II*\x00", b"MM\x00*")):
        return "image/tiff"
    return None


def bytes_to_json_value(value: bytes | bytearray | memoryview) -> Any:
    data = bytes(value)
    mime = image_mime_from_bytes(data)
    if mime is not None:
        encoded = base64.b64encode(data).decode("ascii")
        return f"data:{mime};base64,{encoded}"
    preview = base64.b64encode(data[:128]).decode("ascii")
    return {"type": "binary", "size": len(data), "base64_preview": preview}


def normalize_parquet_value(value: Any) -> Any:
    if isinstance(value, dict):
        result: dict[str, Any] = {}
        image_data_url: str | None = None
        for key, child in value.items():
            key_text = str(key)
            if key_text == "bytes" and isinstance(child, (bytes, bytearray, memoryview)):
                normalized = bytes_to_json_value(child)
                if isinstance(normalized, str) and normalized.startswith("data:image/"):
                    image_data_url = normalized
                else:
                    result[key_text] = normalized
            else:
                result[key_text] = normalize_parquet_value(child)
        if image_data_url is not None:
            return {"type": "image", "data_url": image_data_url, **result}
        return result
    if isinstance(value, list):
        return [normalize_parquet_value(item) for item in value]
    if isinstance(value, tuple):
        return [normalize_parquet_value(item) for item in value]
    if isinstance(value, (bytes, bytearray, memoryview)):
        return bytes_to_json_value(value)
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.startswith(("{", "[")):
            try:
                return normalize_parquet_value(loads_json(stripped))
            except Exception:
                return value
    return value


def discover_parquet_signatures(path: Path) -> tuple[tuple[str, int, int], ...]:
    if path.is_file():
        if path.suffix.lower() != ".parquet":
            raise ValueError(f"Expected a .parquet file, got: {path}")
        files = [path]
    elif path.is_dir():
        files = sorted((item for item in path.rglob("*.parquet") if item.is_file()), key=lambda item: str(item))
    else:
        raise FileNotFoundError(path)

    if not files:
        raise ValueError(f"No .parquet files found under: {path}")

    signatures: list[tuple[str, int, int]] = []
    for file_path in files:
        stat = file_path.stat()
        signatures.append((str(file_path), stat.st_size, stat.st_mtime_ns))
    return tuple(signatures)


@st.cache_data(show_spinner=False)
def build_parquet_sources(signatures: tuple[tuple[str, int, int], ...]) -> tuple[ParquetFileInfo, ...]:
    pq = load_pyarrow_parquet()
    sources: list[ParquetFileInfo] = []
    for path_text, size, mtime_ns in signatures:
        try:
            parquet_file = pq.ParquetFile(path_text)
        except Exception as exc:
            raise ValueError(f"Failed to read parquet metadata from {path_text}: {exc}") from exc
        sources.append(
            ParquetFileInfo(
                path=path_text,
                size=size,
                mtime_ns=mtime_ns,
                row_count=parquet_file.metadata.num_rows,
            )
        )
    return tuple(sources)


def locate_parquet_row(info: DatasetInfo, index: int) -> tuple[ParquetFileInfo, int]:
    if index < 0 or index >= info.sample_count:
        raise IndexError(index)
    remaining = index
    for source in info.parquet_files:
        if remaining < source.row_count:
            return source, remaining
        remaining -= source.row_count
    raise IndexError(index)


@st.cache_data(show_spinner=False, max_entries=32)
def read_parquet_row(path_text: str, size: int, mtime_ns: int, index: int) -> Any:
    del size, mtime_ns
    pq = load_pyarrow_parquet()
    parquet_file = pq.ParquetFile(path_text)
    row_start = 0
    for row_group_idx in range(parquet_file.num_row_groups):
        row_group_rows = parquet_file.metadata.row_group(row_group_idx).num_rows
        if index < row_start + row_group_rows:
            row = parquet_file.read_row_group(row_group_idx).slice(index - row_start, 1).to_pylist()[0]
            return normalize_parquet_value(row)
        row_start += row_group_rows
    raise IndexError(index)


def read_parquet_sample(info: DatasetInfo, index: int) -> Any:
    source, local_index = locate_parquet_row(info, index)
    return read_parquet_row(source.path, source.size, source.mtime_ns, local_index)


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
    mode = infer_parser_mode(path, parser_mode)
    if mode == "parquet":
        signatures = discover_parquet_signatures(path)
        sources = build_parquet_sources(signatures)
        total_rows = sum(source.row_count for source in sources)
        total_size = sum(source.size for source in sources)
        parse_note = f"{len(sources):,} parquet file{'s' if len(sources) != 1 else ''}"
        return DatasetInfo(
            format_name="parquet",
            sample_count=total_rows,
            parse_note=parse_note,
            source_count=len(sources),
            size_bytes=total_size,
            parquet_files=sources,
        )

    size, mtime_ns = file_stat(str(path))
    if mode == "jsonl":
        offsets = build_jsonl_offsets(str(path), size, mtime_ns)
        return DatasetInfo(format_name="jsonl", sample_count=len(offsets), offsets=offsets, size_bytes=size)

    root = load_json_root(str(path), size, mtime_ns)
    chosen_path = collection_path or choose_auto_collection_path(root)
    _, sample_count = get_json_sample(root, chosen_path, 0)
    return DatasetInfo(format_name="json", sample_count=sample_count, root=root, collection_path=chosen_path, size_bytes=size)


def load_current_sample(path: Path, info: DatasetInfo, index: int) -> Any:
    if info.format_name == "parquet":
        return read_parquet_sample(info, index)
    if info.format_name == "jsonl":
        return read_jsonl_sample(path, info.offsets, index)
    sample, _ = get_json_sample(info.root, info.collection_path, index)
    return sample


def sample_source_path(path: Path, info: DatasetInfo, index: int) -> Path:
    if info.format_name == "parquet" and info.parquet_files:
        source, _ = locate_parquet_row(info, index)
        return Path(source.path)
    return path


def sample_count_from_info(info: DatasetInfo) -> int:
    return max(info.sample_count, 0)
