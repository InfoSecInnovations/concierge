import { $ } from "bun";

export default async () => {
	await $`docker container rm --force opensearch-node1`.quiet();
	await $`docker volume rm --force shabti_opensearch-data1`.quiet();
	await $`docker container rm --force keycloak postgres`.quiet();
	await $`docker volume rm --force shabti_postgres_data`.quiet();
	// Compose reuses a container when the service definition is unchanged, so a llama_cpp
	// container created against an older my-models.ini would keep mounting the stale file
	await $`docker container rm --force llama_cpp`.quiet();
};
