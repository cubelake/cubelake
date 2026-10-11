"""Writes to the raw (bronze) zone. URIs are gs://bucket/prefix in GCP, or a local path in tests."""

from fsspec.core import url_to_fs


def partition(root: str, snapshot_date: str) -> str:
    """Hive-style partition that BigLake external tables read as the `snapshot_date` column."""
    return f"{root.rstrip('/')}/snapshot_date={snapshot_date}"


def write_text(uri: str, text: str) -> None:
    fs, path = url_to_fs(uri)
    fs.makedirs(fs._parent(path), exist_ok=True)
    fs.pipe_file(path, text.encode("utf-8"), content_type="application/x-ndjson")
