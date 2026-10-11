"""cubelake-ingest <source> --date YYYY-MM-DD — runs as a Cloud Run job, one source per execution."""

import argparse
from datetime import date


def main() -> None:
    parser = argparse.ArgumentParser(prog="cubelake-ingest")
    parser.add_argument("source", choices=["apple-rss", "apple-itunes"])
    parser.add_argument("--date", type=date.fromisoformat, required=True, help="snapshot date, YYYY-MM-DD")
    args = parser.parse_args()
    snapshot_date = args.date.isoformat()

    # Imports stay inside the branches: each source only loads its own module.
    # Settings() fields come from env vars (pydantic-settings), which type checkers can't see.
    if args.source == "apple-rss":
        from cubelake_ingest.apple_rss import config, ingest

        ingest.ingest(config.Settings(), snapshot_date)  # pyright: ignore[reportCallIssue]
    else:
        from cubelake_ingest.apple_itunes import config, ingest

        ingest.ingest(config.Settings(), snapshot_date)  # pyright: ignore[reportCallIssue]


if __name__ == "__main__":
    main()
