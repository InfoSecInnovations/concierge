# Collaborator Guide

This is for internal use for those who have permissions to manage the repository, but is published here for transparency and easy access by ourselves.

Please also make sure to have read the [Contribution Guidelines](CONTRIBUTING.md) thoroughly as this applies to everyone!

## Versioning

We're using [Python Version Specifiers](https://packaging.python.org/en/latest/specifications/version-specifiers/#version-specifiers) to version our releases. There are some minor differences with semver, so please read that page.

## Branches

- `main` branch contains the latest public release, it should be the same code that people are using if they are up to date.
- `development` branch contains any features we are fairly sure will make it into an upcoming release. Efforts should be made to avoid breaking this branch, and should this occur it should be fixed immediately, as it is meant to allow the team to build on top of a working code base.
- `X.Y.Z` release branches contain only commits relating to the features planned for the release with that number. Making a release branch enables us to keep adding new changes to `development` without polluting the release while we finalize it. A release branch should be in a working state, similar to `development`, it indicates that a bit of polish and testing is needed before publishing.
- feature branches should be used when experimenting or if your code is currently in a broken state.

## Publishing a release

You shouldn't update the version in `bun_installer/package.json` manually, the script will take care of it.

If you have made changes to either of the packages in `concierge_packages` you should manually set the version in the relevant `pyproject.toml`. Make sure to update `requirements.txt` to use the new version. You only need to increment the version when publishing a release as the online versions are only used in the production docker image. Both the development environment and the local docker build use your local versions of the packages. Use pre-release versioning for the packages until doing a major release, at which point you should also set non pre-release versions on the packages.

### Major release

While we're in alpha/beta phase, "major" refers to the second number in the version as we're using `0.X.Y` versions where `X` refers to a major release and `Y` refers to a patch. Once we consider Shabti to be properly production ready, releases will be `1.X.Y`. Major releases and their patches are what we want the general public to be using.

- Make sure to update [CHANGELOG.md](CHANGELOG.md) with the changes that have been implemented since the previous major release.
- Merge the corresponding branch into the `main` branch. Ensure you're only merging features you intend to release, unfinished features need to remain on `development` or a dedicated feature branch.
- Create a release using the script described below.
- Copy appropriate section from CHANGELOG.md into the release description.

### Pre-release versions

For testing purposes it may be required to publish a release, as we need to verify that Shabti and its Configurator work in an environment identical to production, and this can only be achieved by publishing the Python dependencies to PyPI and the Docker image to Docker Hub.

- For general testing you can publish from any branch, a release candidate should be published from the `X.Y.Z` release branch once you believe its contents are ready for a major release and just need some testing first.
- For general testing use `0.XaN` or `0.X.YaN` for a patch, for release candidates use `0.XrcN` or `0.X.YrcN` for a patch.
- Create a release using the script described below.

### Release script

We have an all in one release script that requires a bit of setup up front but allows you to quickly push a release to GitHub with all the dependencies published to their platforms once you have it configured.

#### Requirements

- Permission to push changes to this repository on GitHub
- Permission to push images to the `infosecinnovations/concierge` repository on Docker Hub
- Permission to upload new versions of `concierge-util` and `isi-util` to PyPI
- Bun 1.2.1
- Python 3.12
- git command line configured to be able to use your GitHub account
- gh command line (git and gh are not the same thing!) configured to be able to use your GitHub account
- Docker >= 25.0.3 configured to be able to use your Docker Hub account from the command line
- a PyPI API token
- fast upload and download speed (otherwise it takes a really really long time!)

#### Running the script

- Make sure you're using the git branch you wish to release from.
- Navigate to the `bun_installer` subdirectory.
- Run `bun run publish.ts`.
- Input the new version number for your release, make sure it's different from the current one to avoid any conflicts.
- If there were any updates to the Python packages you will be prompted for your PyPI API token.
- If you got all the requirements set up correctly the script should manage to do the following:
    - Set the version in `bun_installer/package.json`.
    - Upload new versions of the Python packages to PyPI if you incremented their versions locally.
    - Build, tag and upload the Docker image from your local files.
    - Commit and push changes to GitHub.
    - Build Windows, Linux and MacOS executable files and zip them.
    - Create a GitHub tag and release from the current branch with the executable files attached to it.

If everything went OK you will be able to see your published release on GitHub, congratulations!

## Building the Keycloak JavaScript archive

Keycloak requires policies and other JavaScript providers to be zipped to a `.jar` file and placed in a specific directory. You can run the Docker compose file called `docker-compose-zip-policy.yml` which will zip the contents of `keycloak_javascript` and place them in the file that gets mounted to the Keycloak container.