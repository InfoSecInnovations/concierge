FROM astral/uv:0.11.1-python3.14-trixie-slim AS base

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/
WORKDIR /app/shabti/
ENV UV_LINK_MODE=copy
ENV UV_HTTP_TIMEOUT=500
CMD [ "uv", "run", "docker_run.py" ]

EXPOSE 15131

RUN --mount=type=cache,target=/root/.cache/uv --mount=type=bind,source=pyproject.toml,target=pyproject.toml uv sync --no-install-project
COPY . /app/shabti/
RUN --mount=type=cache,target=/root/.cache/uv uv sync
RUN --mount=type=cache,target=/root/.cache uv pip install -r requirements.txt
