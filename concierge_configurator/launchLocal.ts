import { $ } from "bun"

await $`docker compose -f ./docker_compose/docker-compose-local.yml build`
await $`docker compose -f ./docker_compose/docker-compose-local.yml up -d`