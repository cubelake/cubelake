"""cubelake-extract <source> --date YYYY-MM-DD — runs as a Cloud Run job, one source per execution."""

import argparse
from datetime import date


def main() -> None:
    parser = argparse.ArgumentParser(prog="cubelake-extract")
    parser.add_argument("source", choices=["apple-rss", "apple-itunes"])
    parser.add_argument("--date", type=date.fromisoformat, required=True, help="snapshot date, YYYY-MM-DD")
    args = parser.parse_args()
    snapshot_date = args.date.isoformat()

    # Imports stay inside the branches: each source only loads its own module.
    if args.source == "apple-rss":
        from cubelake_extract.apple_rss import config, pipeline

        pipeline.extract(config.Settings(), snapshot_date)
    else:
        from cubelake_extract.apple_itunes import config, pipeline

        pipeline.extract(config.Settings(), snapshot_date)


if __name__ == "__main__":
    main()
