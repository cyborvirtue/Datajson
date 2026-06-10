from __future__ import annotations

import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
HISTORY_FILE = PROJECT_ROOT / ".datajson_history.json"
MAX_HISTORY = 20


def load_path_history() -> list[str]:
    if not HISTORY_FILE.exists():
        return []
    try:
        data = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if not isinstance(data, list):
        return []
    history: list[str] = []
    for item in data:
        if isinstance(item, str) and item.strip() and item not in history:
            history.append(item.strip())
    return history[:MAX_HISTORY]


def save_path_history(history: list[str]) -> None:
    clean_history: list[str] = []
    for item in history:
        if item and item not in clean_history:
            clean_history.append(item)
    HISTORY_FILE.write_text(
        json.dumps(clean_history[:MAX_HISTORY], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def record_path_history(path: Path) -> None:
    try:
        normalized = str(path.expanduser().resolve())
    except OSError:
        normalized = str(path.expanduser())
    if not normalized:
        return
    history = [item for item in load_path_history() if item != normalized]
    save_path_history([normalized, *history])
