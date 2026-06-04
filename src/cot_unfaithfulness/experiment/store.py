"""JSONL persistence helpers (append-only, thread-safe).

Used for crash-safe, resumable runs: each phase appends records as they complete
and skips work whose key already exists on disk.
"""

from __future__ import annotations

import threading
import warnings
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel, ValidationError

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
        lines = [ln.strip() for ln in f if ln.strip()]
    for i, line in enumerate(lines):
        try:
            records.append(model.model_validate_json(line))
        except ValidationError:
            # A crash mid-append (e.g. balance exhausted) can leave the final
            # line truncated. Tolerate that so the completed portion resumes;
            # a malformed non-final line signals real corruption — surface it.
            if i == len(lines) - 1:
                warnings.warn(f"skipping truncated final line in {path}", stacklevel=2)
                continue
            raise
    return records
