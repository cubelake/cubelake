import argparse
import json

from apple_rss.config import Settings

from apple_rss import pipeline


def main() -> None:
    parser = argparse.ArgumentParser(prog="apple-rss")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("extract", help="fetch top charts into bronze").add_argument("--date", required=True)
    sub.add_parser("pending", help="print bronze dates not yet in silver (JSON, last line)")
    sub.add_parser("transform", help="dbt: bronze -> silver_top_apps").add_argument("--date", required=True)
    args = parser.parse_args()

    settings = Settings()
    match args.command:
        case "extract":
            pipeline.extract(settings, args.date)
        case "pending":
            print(json.dumps(pipeline.pending(settings)), flush=True)
        case "transform":
            pipeline.transform(settings, args.date)


if __name__ == "__main__":
    main()
