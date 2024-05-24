# Collaborator Guide

This is for internal use for those who have permissions to manage the repository, but is published here for transparency and easy access by ourselves.

## Linting

We have the ruff linter configured to catch common errors and formatting issues. After installing dependencies please run `pre-commit install` inside the venv to configure the pre-commit linting hook.

## Versioning

We will be using [semver](https://semver.org/) to number releases, i.e. MAJOR.MINOR.PATCH. While still in Alpha and Beta phases versions will be 0.x.x. To clarify that we expect bugs and other issues we prefix the release names with "Alpha" during initial development phase, and "Beta" when we feel we're close to 1.0.0 but not quite able to call it production ready.

## Branches

- `main` branch contains the latest public release, it should be the same code that people are using if they are up to date.
- `development` branch contains any features we are fairly sure will make it into an upcoming release. Efforts should be made to avoid breaking this branch, and should this occur it should be fixed immediately, as it is meant to allow the team to build on top of a working code base.
- `x.x.x` release branches contain only commits relating to the features planned for the release with that number. Making a release branch enables us to keep adding new changes to `development` without polluting the release while we finalize it. A release branch should be in a working state, similar to `development`, it indicates that a bit of polish and testing is needed before publishing.
- feature branches should be used when experimenting or if your code is currently in a broken state.

## Publishing a release

- Make sure to update [CHANGELOG.md](CHANGELOG.md) with the changes that have been implemented since the previous release.
- Merge the corresponding branch into the `main` branch. Ensure you're only merging features you intend to release, unfinished features need to remain on `development` or a dedicated feature branch.
- Go to the Releases page, and create a new release from the `main` branch. Prefix the title with "Alpha" or "Beta" if appropriate. In the current stage, all releases should be prefixed with "Alpha"!
- Copy appropriate section from CHANGELOG.md into the release description.

### TODO

Use script to automate publishing a release!