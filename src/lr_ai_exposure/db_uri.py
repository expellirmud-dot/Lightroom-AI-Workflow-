"""Shared Windows-safe SQLite read-only URI helper.

Both cache_probe and cache_extractor import from here to avoid a
circular import and to keep the URI building logic in one place.

On Windows, sqlite3 requires a URI of the form
`file:///C:/path/to/db.sqlite?mode=ro`. The path after the
drive colon must use FORWARD slashes, and the URI needs three
leading slashes. A backslash path or a missing third slash silently
opens the wrong/empty database and returns zero rows / DB_ERROR.
"""
from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import quote


def safe_sqlite_uri(path: str) -> str:
    """Return a Windows-safe sqlite3 URI for the given DB path."""
    p = Path(path).resolve()
    if os.name == "nt":
        # Native Windows form: D:\foo -> D:/foo (forward slashes).
        raw = str(p).replace("\\", "/")
        safe = quote(raw, safe=":/")
        return f"file:///{safe}"
    safe = quote(p.as_posix(), safe=":/")
    return f"file:{safe}"
