"""Storage helpers. URIs are a local path (dev) or gs://bucket/prefix (production)."""

from fsspec import AbstractFileSystem
from fsspec.core import url_to_fs


def _fs(uri: str) -> tuple[AbstractFileSystem, str]:
    return url_to_fs(uri)


def ensure_dir(uri: str) -> None:
    """DuckDB won't create parent directories for local COPY TO; object stores don't need this."""
    fs, path = _fs(uri)
    fs.makedirs(path, exist_ok=True)


def snapshot_dates(uri: str) -> set[str]:
    """Dates of the `snapshot_date=YYYY-MM-DD/` partitions directly under `uri`."""
    fs, path = _fs(uri)
    try:
        entries = fs.ls(path, detail=False)
    except FileNotFoundError:
        return set()
    return {e.rstrip("/").split("snapshot_date=")[-1] for e in entries if "snapshot_date=" in e}
