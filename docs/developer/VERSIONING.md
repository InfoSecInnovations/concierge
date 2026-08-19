# Versioning

The process for incrementing Shabti versions and dependency versions.

## Shabti

Shabti has an overall version which is set in the repository root's `package.json`. The REST API, Web UI and CLI components of Shabti are included under this version number. In the future we may decide to decouple the component versions but during the current phase of development changes will generally be implemented across all of these components. We follow the semver versioning scheme.

### Shabti Configurator

Since the introduction of code signing, we've decided to make the configurator/launcher app follow a separate versioning scheme. This allows us to release new versions of Shabti without having to use a signing credit to sign the executable again if it was not modified.

### Packages

Several dependencies used by components of Shabti are released as packages so we can reuse them across multiple components and make them available to projects building upon Shabti.

- **isi-util** - PyPI
- **shabti-api-client** - PyPI
- **shabti-keycloak** - PyPI
- **shabti-types** - PyPI
- **shabti-util** - PyPI
- **@infosecinnovations/shabti-api-client** - NPM

It is not necessary to publish changes to these when using the development environment as the source files are pulled locally. Whenever a new version of Shabti is being pushed the version of each dependency that changed since the last release must be incremented, along with every pin referring to it. This is done automatically, see [Releasing](#releasing).

The version of each Python package is only declared in its own `pyproject.toml` under `python_packages`. The Shabti API and Web projects depend on them by name and always install them from the local source. Their lockfiles record the version of each package, so incrementing one makes those lockfiles out of date; this is handled for you by the install, launch, test and publish processes (see [LOCKFILES.md](./LOCKFILES.md)).

### Pre 1.0 versions

Until Shabti reaches the 1.0 feature set we will use 0.x.y versions where x represents a new feature set and y is used for any hotfixes.

### Pre-release versions

Before publishing an official release (i.e. an "x" in the 0.x.y scheme) we may publish a number of pre-release versions to try out the publishing process and test how Shabti runs in a production environment. We generally use alpha versions when the next version is still a work in progress, and will publish release candidate versions when the development version of Shabti is feature complete for the next release and we need to try it before officially releasing. Any of the dependencies which have changed since the previous release will also use alpha and release candidate versioning.

## Releasing

Versions are incremented by the publish workflows, not by hand. Both `Publish Shabti` and `Publish Launcher` take a **release type** (`alpha`, `rc` or `latest`) and a **release importance** (`major`, `minor` or `patch`), and both run `versioning/bump.ts`, which works out which components changed, bumps those, and rewrites every reference to the versions it moved.

`Publish Shabti` covers the overall version, the API and Web images, the CLI, the Node client and the Python packages. `Publish Launcher` covers the configurator and the overall version, since it is the only workflow that builds and signs the launcher.

Each workflow only builds one of the two executables in the release zips, so it carries the other one forward from the release it follows. `alpha` and `rc` runs are marked as prereleases on GitHub, which is why the carry-forward asks for that release by tag rather than for the "latest" release, which would skip past every prerelease.

To see what a release would do without publishing anything, dispatch either workflow with `dry_run`, or run it locally:

```sh
bun run bump -- --release-type alpha --importance major --dry-run
```

### Manual steps

- **`configurator-versions.json`** - `configuratorMinVersion` is the oldest configurator that can install the release being made. Bump it when Shabti starts relying on something a configurator did not have.
- **`shabti_configurator/compatibility.json`** - `minShabtiVersion` is the oldest release this configurator can install. Bump it when the configurator drops support for older releases.

## Third party dependencies

### Runtimes

- **uv**
- **Python**
- **Bun**

The above should be pinned to non breaking ranges to avoid surprises when publishing and releasing.

When moving to a new release number we will pin these to the latest versions.

- **Docker**

We don't expect Docker to release versions which would break existing images

### Packages

The components of Shabti themselves depend on a variety of packages available in the Python and JavaScript ecosystems. We try to ensure that all of these are pinned to non breaking version ranges, and if we notice that any packages are introducing breaking changes without respecting the appropriate versioning scheme we will lock them more strictly to specific versions.

We keep an eye on possible vulnerabilities in these packages and also look out for new features which we wish to leverage. During development of a new release number we evaluate the need to upgrade dependencies.

Packages of particular interest are:

- **shiny** - this framework is still receiving many feature updates and these will often bring improvements and fixes to Shabti's web UI.
- **fastapi** - the REST API is built on this.
- **unstructured** - we use this to ingest all documents currently, so it's worth checking for improvements and fixes.
- **opensearch-py** - ensure this is synchronized with the OpenSearch version being used in our Docker Compose.
- **python-keycloak** - ensure this is compatible with the Keycloak version being used in our Docker Compose.
- **@keycloak/keycloak-admin-client** - ensure this is compatible with the Keycloak version being used in our Docker Compose.

### Docker images

- **ollama/ollama** - this image is very frequently updated and causes large downloads each time this happens, it has been pinned to a minor version to reduce the amount of time spent downloading.
- **opensearchproject/opensearch, opensearchproject/opensearch-dashboards** - these images follow a coupled versioning scheme and should be updated at the same time, pinned to minor version.
- **quay.io/keycloak/keycloak** - Pinned to minor version.
- **postgres** - Keycloak uses this as storage, there is generally more flexibility here so we just restrict it to a major version.
- **astral/uv** - Base image used in the Shabti Docker images, pinned to minor Python version.

When moving to a new release number we will pin these to the latest versions.