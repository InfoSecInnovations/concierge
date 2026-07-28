import { $ } from "bun";

export default async () => {
	await $`docker container rm --force opensearch-node1`.quiet();
	await $`docker volume rm --force shabti_opensearch-data1`.quiet();
	await $`docker container rm --force keycloak postgres`.quiet();
	await $`docker volume rm --force shabti_postgres_data`.quiet();
};
