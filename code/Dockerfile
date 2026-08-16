FROM python:3.13-slim-trixie AS builder
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \ 
    UV_LINK_MODE=copy 

ENV UV_PYTHON_DOWNLOAD=0

WORKDIR /app

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    uv sync --locked --no-install-project --no-dev

COPY . /app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev

FROM python:3.13-slim-trixie

RUN groupadd -r appuser && useradd -r -g appuser appuser


COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/api /app/api
COPY --from=builder /app/core /app/core
COPY --from=builder /app/main.py /app/main.py
COPY --from=builder /app/alembic /app/alembic
COPY --from=builder /app/scripts /app/scripts
COPY --from=builder /app/static /app/static
COPY --from=builder /app/templates /app/templates
COPY --from=builder /app/alembic.ini /app/alembic.ini
COPY --from=builder /app/crud.py /app/crud.py
COPY --from=builder /app/exception.py /app/exception.py
COPY --from=builder /app/models.py /app/models.py
COPY --from=builder /app/schemas.py /app/schemas.py
COPY --from=builder /app/jobs.py /app/jobs.py
COPY --from=builder /app/logging_config.py /app/logging_config.py
COPY --from=builder /app/metrics.py /app/metrics.py
COPY --from=builder /app/middleware.py /app/middleware.py
COPY --from=builder /app/utils.py /app/utils.py

ENV PATH="/app/.venv/bin:$PATH"


USER appuser
WORKDIR /app

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]


