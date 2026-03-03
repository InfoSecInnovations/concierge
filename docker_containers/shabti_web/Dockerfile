FROM astral/uv:python3.12-trixie-slim

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/
WORKDIR /shabti_web/
ENV UV_LINK_MODE=copy
RUN --mount=type=cache,target=/root/.cache/uv --mount=type=bind,source=pyproject.toml,target=pyproject.toml uv sync --no-install-project
COPY . /shabti_web/
RUN --mount=type=cache,target=/root/.cache/uv uv sync --locked
RUN uv pip install -r requirements.txt
CMD [ "uv", "run", "docker_run.py" ]

EXPOSE 15130