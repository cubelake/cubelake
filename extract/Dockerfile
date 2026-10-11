# Cloud Run job image: `cubelake-extract <apple-rss|apple-itunes> --date YYYY-MM-DD`
FROM python:3.13-slim

COPY --from=ghcr.io/astral-sh/uv:0.11.32 /uv /bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never
WORKDIR /app

COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --locked --no-dev --no-install-project
COPY src ./src
RUN uv sync --locked --no-dev

RUN useradd --uid 10001 --no-create-home --shell /usr/sbin/nologin app
USER app
ENV PATH="/app/.venv/bin:$PATH"
ENTRYPOINT ["cubelake-extract"]
