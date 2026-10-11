import argparse
import json

from appstore_analytics.config import Settings

from appstore_analytics import pipeline


def main() -> None:
    parser = argparse.ArgumentParser(prog="appstore-analytics")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("pending", help="print dates to process (JSON, last line)").add_argument(
        "--stage", choices=["silver", "gold"], required=True
    )
    sub.add_parser("silver", help="join rss + itunes for one day").add_argument("--date", required=True)
    sub.add_parser("gold-daily", help="fct_top_apps + fct_genre_stats for one day").add_argument("--date", required=True)
    sub.add_parser("dim-apps", help="rebuild dim_apps (SCD1, latest state per app)")
    sub.add_parser("rank-history", help="rebuild fct_app_rank_history from all snapshots")
    args = parser.parse_args()

    settings = Settings()
    match args.command:
        case "pending":
            dates = pipeline.pending_silver(settings) if args.stage == "silver" else pipeline.pending_gold(settings)
            print(json.dumps(dates), flush=True)
        case "silver":
            pipeline.build_silver(settings, args.date)
        case "gold-daily":
            pipeline.build_gold_daily(settings, args.date)
        case "dim-apps":
            pipeline.build_dim_apps(settings)
        case "rank-history":
            pipeline.build_rank_history(settings)


if __name__ == "__main__":
    main()
