"""JSONL persistence helpers (append-only, thread-safe).

Used for crash-safe, resumable runs: each phase appends records as they complete
and skips work whose key already exists on disk.
"""

from __future__ import annotations

import threading
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel

M = TypeVar("M", bound=BaseModel)

_write_lock = threading.Lock()


def append_jsonl(path: Path, obj: BaseModel) -> None:
    """Append one model as a JSON line (thread-safe)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    line = obj.model_dump_json()
    with _write_lock:
        with path.open("a") as f:
            f.write(line + "\n")


def load_jsonl(path: Path, model: type[M]) -> list[M]:
    """Load all records of ``model`` from a JSONL file (empty if missing)."""
    if not path.exists():
        return []
    records: list[M] = []
    with path.open() as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(model.model_validate_json(line))
    return records
