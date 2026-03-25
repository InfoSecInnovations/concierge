FROM astral/uv:0.11.1-python3.14-trixie-slim

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/
WORKDIR /app/shabti_web/
ENV UV_LINK_MODE=copy
RUN --mount=type=cache,target=/root/.cache/uv --mount=type=bind,source=pyproject.toml,target=pyproject.toml --mount=type=bind,source=uv.lock,target=uv.lock uv sync --no-install-project
COPY . /app/shabti_web/
RUN --mount=type=cache,target=/root/.cache/uv uv sync --locked
RUN --mount=type=cache,target=/root/.cache uv pip install -r requirements.txt
CMD [ "uv", "run", "docker_run.py" ]

EXPOSE 15130