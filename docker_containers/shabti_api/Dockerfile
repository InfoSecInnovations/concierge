FROM astral/uv:python3.12-trixie-slim AS cpu

RUN rm -f /etc/apt/apt.conf.d/docker-clean; echo 'Binary::apt::APT::Keep-Downloaded-Packages "true";' > /etc/apt/apt.conf.d/keep-cache
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
  --mount=type=cache,target=/var/lib/apt,sharing=locked \
/bin/sh -c set -eux; apt-get update; apt-get install -y --no-install-recommends poppler-utils pandoc tesseract-ocr libreoffice libgl1 libglib2.0-0

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/
COPY . /shabti/
WORKDIR /shabti/
ENV UV_LINK_MODE=copy
RUN --mount=type=cache,target=/root/.cache/uv --mount=type=bind,source=pyproject.toml,target=pyproject.toml uv sync --no-install-project
COPY . /shabti/
RUN --mount=type=cache,target=/root/.cache/uv uv sync --locked
CMD [ "python", "docker_run.py" ]

EXPOSE 15130

FROM cpu AS cuda
RUN --mount=type=cache,target=/root/.cache/uv uv sync --extra cu126