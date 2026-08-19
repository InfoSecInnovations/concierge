## Parameters

The initial attempt using a version number and a tag type is flawed.

- use semver's ReleaseType (major, premajor, minor, preminor, patch, prepatch, prerelease, release) which covers all the scenarios.
- add optional `--preid` parameter, options in GitHub workflow will be `alpha`, `beta` and `rc`. This parameter is ignored if the release is stable. If ommitted for a prerelease, it will keep the existing prerelease tag. If we're bumping a stable version to prerelease, the default must be `alpha`.
- use a `--paths` list with all the paths to verify, this makes the tool a lot more flexible, easier to adapt to automated testing, and potentially reusable in other projects.
- the root path is a special case and doesn't need to be included in the `--paths` list, for now we assume the root always uses `package.json`.

## Versioning

- uv and semver both use 0 indexed prereleases, but PEP440 considers the 0 to be implicit so it will produce X.Y.Za as an equivalent to semver X.Y.Z-alpha.0
- use `uv --bump` and `bun pm version` instead of writing directly to `package.json` or `pyproject.toml`, we still have to use `semver.inc` to calculate the version as bun does some nonstandard stuff with incrementing.
- we will delete all the prerelease versions including the tags (for the purposes of the initial run of this system)
- we will manually bump the CLI to release (oversight) before running the system
- if no packages changed at all and we're not doing a release, that's an error state, if not the root will always bump. We have immutable releases enabled so we won't be able to overwrite existing releases anyway
- if multiple components changed, we still only increment the root version by 1 version
- if we chose `release` type but any of the components are already stable but changed, we throw an error, this means we probably need to calculate all the versions first in a dry run before actually applying the changes, we have to make sure to capture linked dependencies too (see below)

## Diffing

- Can't really walk the git history as this gets complex with branches and stuff.
- We should go back through each release to find the release in which the relevant `package.json` or `pyproject.toml` had its version changed, this isn't always chronological as we may have a prerelease branch for the next version but be pushing fixes to the release version at the same time. Sort existing GitHub tags by semver ordering and filter by less than or equal to current release.
- Read each component's version using `git show <tag>:<version file>`, we're searching for the oldest commit with a version matching current.
- If no match is found, we treat as changed/new.
- Git diff the directory against the commit where the version was changed to see if anything changed.
- Just use git command as we already have that installed on the runner and the local machine.

## Updating dependency links

- Update version pins anywhere a precise version of the project is mentioned (`package.json`, `requirements.txt`, `pyproject.toml`). While it is 3 files currently in our specific project, we want this check to be automated and generic to not break the process if the repo structure changes in the future.
- Any project which depends on the updated project also gets incremented even if the dependency is a local install as this means the bundled output will have changed.
- Loop the updating routine until no diffs are found, bookmark the already bumped paths to avoid infinite looping
- Rebuild `shabti-components.json`

## Workflow improvements

- The command should only output the bare minimum information required by other workflow steps, we do not need a full "report", just enough that the automation works.
- There should be a workflow to release the launcher and the shabti stack at the same time which will be useful when a release increments the launcher and other components at the same time. Now that we can detect diffs in packages, we can just gate the code signing part behind changes in the configurator, if no change, pull the file from the previous release as before (previous release must be semver previous and not chronological). It should be possible to merge both launcher flows.

## Testing

- Create a mock repo to run the tests in, we should avoid modifying the actual repo at any cost!

We should make sure the testing is fairly exhaustive as errors in this automated process could prove troublesome.