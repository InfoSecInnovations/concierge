// This script was implemented to enable automated tests to tear down Concierge
// Use at your own risk for other purposes!

import { $ } from "bun";

// we don't remove Ollama because the service is never modified and it takes a long time to re-download the models
// we run the commands sequentially because you can't remove a volume while the container is still using it
await $`docker container rm --force concierge`,
	await $`docker container rm --force opensearch-node1`,
	await $`docker volume rm --force concierge_opensearch-data1`;
await $`docker container rm --force keycloak postgres`;
await $`docker volume rm --force concierge_postgres_data`;
