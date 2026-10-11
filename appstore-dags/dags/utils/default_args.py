from datetime import datetime, timedelta

_common = {
    "owner": "data-engineering",
    "start_date": datetime(2026, 4, 20),
    "depends_on_past": False,
}

bronze_args = {
    **_common,
    "retries": 1,
    "retry_delay": timedelta(seconds=30),
}


silver_args = {
    **_common,
    "retries": 2,
    "retry_delay": timedelta(minutes=1),
}


gold_args = {
    **_common,
    "retries": 3,
    "retry_delay": timedelta(minutes=2),
}
