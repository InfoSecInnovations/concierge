ARG ACCELERATION_TYPE=cpu

FROM astral/uv:0.11.1-python3.14-trixie-slim AS base

RUN rm -f /etc/apt/apt.conf.d/docker-clean; echo 'Binary::apt::APT::Keep-Downloaded-Packages "true";' > /etc/apt/apt.conf.d/keep-cache
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
  --mount=type=cache,target=/var/lib/apt,sharing=locked \
/bin/sh -c set -eux; apt-get update; apt-get install -y --no-install-recommends poppler-utils pandoc tesseract-ocr libreoffice libgl1 libglib2.0-0

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/
WORKDIR /app/shabti/
ENV UV_LINK_MODE=copy
ENV UV_HTTP_TIMEOUT=500
CMD [ "uv", "run", "docker_run.py" ]

EXPOSE 15131

FROM base AS cpu
RUN --mount=type=cache,target=/root/.cache/uv --mount=type=bind,source=pyproject.toml,target=pyproject.toml --mount=type=bind,source=uv.lock,target=uv.lock uv sync --no-install-project --no-sources --no-dev --extra cpu

FROM base AS cuda
RUN --mount=type=cache,target=/root/.cache/uv --mount=type=bind,source=pyproject.toml,target=pyproject.toml --mount=type=bind,source=uv.lock,target=uv.lock uv sync --no-install-project --no-sources --no-dev --extra cu126

FROM ${ACCELERATION_TYPE} AS final
COPY . /app/shabti/
RUN --mount=type=cache,target=/root/.cache/uv uv sync --locked  --no-sources --no-dev
RUN --mount=type=cache,target=/root/.cache uv pip install -r requirements.txt
