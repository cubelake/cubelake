"""Storage helpers. URIs are a local path (dev) or gs://bucket/prefix (production)."""

import duckdb
from fsspec import AbstractFileSystem
from fsspec.core import url_to_fs


def _fs(uri: str) -> tuple[AbstractFileSystem, str]:
    return url_to_fs(uri)


def write_text(uri: str, text: str) -> None:
    fs, path = _fs(uri)
    fs.makedirs(fs._parent(path), exist_ok=True)
    fs.pipe_file(path, text.encode("utf-8"))


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


def duckdb_connect(*uris: str) -> duckdb.DuckDBPyConnection:
    """DuckDB connection that can read the given URIs (registers gcsfs for gs:// with ADC)."""
    con = duckdb.connect()
    for protocol in {uri.split("://")[0] for uri in uris if "://" in uri}:
        fs, _ = url_to_fs(f"{protocol}://")
        con.register_filesystem(fs)
    return con
