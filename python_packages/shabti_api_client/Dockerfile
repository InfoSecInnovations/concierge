FROM astral/uv:python3.12-trixie-slim AS base

COPY --from=python_packages ./shabti_types /python_packages/shabti_types/
COPY --from=python_packages ./shabti_keycloak /python_packages/shabti_keycloak/
COPY --from=python_packages ./shabti_api_client /python_packages/shabti_api_client/

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/
ENV UV_LINK_MODE=copy

WORKDIR /python_packages/shabti_api_client/
RUN --mount=type=cache,target=/root/.cache/uv uv add --editable ../shabti_types/ ../shabti_keycloak
RUN --mount=type=cache,target=/root/.cache/uv uv sync

CMD ["uv", "run", "pytest"]


