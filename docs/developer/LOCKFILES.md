# Lockfiles

`docker_containers/shabti_api` and `docker_containers/shabti_web` declare the Shabti packages
(`isi-util`, `shabti-util`, `shabti-types`, `shabti-keycloak`, `shabti-api-client`) as normal
dependencies, with `[tool.uv.sources]` pointing at `/app/python_packages/<name>`. Both Docker
targets install them from there, `local` as editable installs and `online` with `--no-editable` so
they're baked into the published image. They're depended on by name only, since uv doesn't check a
version specifier against a local source. `[tool.uv.sources]` is not included in published package
metadata, so anything installing these packages from PyPI still gets the versions pinned there.

## Regenerating

The Docker builds use `uv sync --locked`, so the lockfiles have to be up to date before a build.
This happens automatically: installing or launching the local version from the configurator,
running the tests, rebuilding a devcontainer, running `publish.ts` and the publish workflow all
regenerate them first. Changing a dependency is a matter of editing the `pyproject.toml` and
launching again.

To do it by hand, from the repository root:

```
bun run lock
```

Those source paths only exist inside the container, so `uv lock` has to run in one. That's what
[docker_containers/docker-compose-uv-lock.yml](../../docker_containers/docker-compose-uv-lock.yml)
is for — it mounts both projects along with `python_packages` and writes the lockfiles back to the
repository. On Linux, set `UV_LOCK_USER` to `"$(id -u):$(id -g)"` so they aren't written as root.

A running dev container also keeps itself in step: its command is `uv run docker_run.py`, and
`uv run` re-syncs the environment on startup against the bind-mounted `pyproject.toml` and
`uv.lock`, updating the lockfile through the mount if it needs to.

Running `uv lock` or `uv sync` on the host in these two directories will fail to find
`/app/python_packages`. The packages in `python_packages` use relative source paths and can be
locked and synced normally.
