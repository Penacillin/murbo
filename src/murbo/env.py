"""Minimal, cross-platform ``.env`` loader (no dependency, no shell tricks).

Reads ``KEY=value`` lines from a ``.env`` file and puts them into ``os.environ`` so the
vision providers find their API keys the same way on Windows, macOS and Linux — without
needing ``source .env`` (which is POSIX-shell only). Real environment variables always
win over file values, so an exported key is never clobbered.
"""

from __future__ import annotations

import os
from pathlib import Path


def load_dotenv(path: str | Path = ".env") -> bool:
    """Load ``KEY=value`` pairs from *path* into ``os.environ`` (existing keys untouched).

    Returns ``True`` if a file was found and read. Lines that are blank or start with ``#``
    are ignored; surrounding quotes and an optional ``export `` prefix are stripped.
    """
    p = Path(path)
    if not p.is_file():
        return False
    for raw in p.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith("export "):
            line = line[len("export ") :]
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value
    return True
