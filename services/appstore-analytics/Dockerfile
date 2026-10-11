# Build from this directory: docker build -t appstore-analytics:local .
FROM python:3.13-slim

COPY --from=ghcr.io/astral-sh/uv:0.11.32 /uv /bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never

WORKDIR /app

# Dependencies first (cached until uv.lock changes)
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --locked --no-dev --no-install-project

COPY src ./src
COPY dbt ./dbt
RUN uv sync --locked --no-dev

# Runs as an unprivileged user; dbt writes its artifacts to /tmp so the app dir stays read-only
RUN useradd --uid 10001 --no-create-home --shell /usr/sbin/nologin app
USER app
ENV PATH="/app/.venv/bin:$PATH" \
    DBT_TARGET_PATH=/tmp/dbt/target \
    DBT_LOG_PATH=/tmp/dbt/logs \
    DBT_SEND_ANONYMOUS_USAGE_STATS=false

ENTRYPOINT ["appstore-analytics"]
