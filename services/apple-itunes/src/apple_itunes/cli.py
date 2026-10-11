import argparse
import json

from apple_itunes.config import Settings

from apple_itunes import pipeline


def main() -> None:
    parser = argparse.ArgumentParser(prog="apple-itunes")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("extract", help="look up charted apps into bronze").add_argument("--date", required=True)
    sub.add_parser("pending", help="print dates to process (JSON, last line)").add_argument(
        "--stage", choices=["extract", "transform"], required=True
    )
    sub.add_parser("transform", help="dbt: bronze -> silver_itunes_app_details").add_argument("--date", required=True)
    args = parser.parse_args()

    settings = Settings()
    match args.command:
        case "extract":
            pipeline.extract(settings, args.date)
        case "pending":
            dates = pipeline.pending_extract(settings) if args.stage == "extract" else pipeline.pending_transform(settings)
            print(json.dumps(dates), flush=True)
        case "transform":
            pipeline.transform(settings, args.date)


if __name__ == "__main__":
    main()
