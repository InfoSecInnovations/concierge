# Collaborator Guide

This is for internal use for those who have permissions to manage the repository, but is published here for transparency and easy access by ourselves.

Please also make sure to have read the [Contribution Guidelines](CONTRIBUTING.md) thoroughly as this applies to everyone!

## Branches

- `main` branch contains the latest public release, it should be the same code that people are using if they are up to date.
- `development` branch contains any features we are fairly sure will make it into an upcoming release. Efforts should be made to avoid breaking this branch, and should this occur it should be fixed immediately, as it is meant to allow the team to build on top of a working code base.
- `X.Y.Z` release branches contain only commits relating to the features planned for the release with that number. Making a release branch enables us to keep adding new changes to `development` without polluting the release while we finalize it. A release branch should be in a working state, similar to `development`, it indicates that a bit of polish and testing is needed before publishing.
- feature branches should be used when experimenting or if your code is currently in a broken state.

## Building the Keycloak JavaScript archive

Keycloak requires policies and other JavaScript providers to be zipped to a `.jar` file and placed in a specific directory. You can run the Docker compose file called `docker-compose-zip-policy.yml` in the `zip_keycloak_policies` directory which will zip the contents of `policies` and place them in the file that gets mounted to the Keycloak container.

## Versioning

See [Versioning](docs/developer/VERSIONING.md)