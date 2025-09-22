Fully automating the whole test sequence is a work in progress, eventually we would like to be able to run a single command and have this all happen by itself. However we must first create all the steps manually and ensure the sequence works before attempting to automate the whole thing.

## Security Disabled

- Using the configurator delete the OpenSearch service (this removes the container and associated storage, this completely nuking the data). It's important we start with a blank slate.
- Navigate to the `tests_docker_compose` subdirectory of the repository
- `docker compose --env-file security-disabled-env build` (if you don't do this, changes made since you last locally ran shabti will not be applied)
- `docker compose --env-file security-disabled-env up --attach shabti` will run the tests and show the output in the console. You can also use the docker logs if you need to retrieve this result later.

## Security Enabled

- Using the configurator delete the OpenSearch and Keycloak services (this removes the container and associated storage, this completely nuking the data). It's important we start with a blank slate.
- Navigate to the `tests_docker_compose` subdirectory of the repository
- `bun --env-file=security-enabled-env run ./prepareSecurity.ts`
- wait a bit, this does some of the same stuff that a full install does!
- `docker compose --env-file security-enabled-env --env-file .env up --attach shabti` will run the tests and show the output in the console. You can also use the docker logs if you need to retrieve this result later.

Note that the paths in the env file seem weird because they are relative to the compose file that uses them rather than the CWD