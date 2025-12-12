import { $ } from "bun";
import * as dotenv from "dotenv";
import nukeExisting from "./nukeExisting";

dotenv.config({ path: "security-disabled-env", override: true, quiet: true });

while (true) {
	await nukeExisting();
	await $`docker container rm --force shabti`.quiet();
	console.log(
		"building Docker Compose... (can take some time if there are updates to the dependencies)",
	);
	await $`docker compose --env-file security-disabled-env -f ./docker-compose-client-test-ollama.yml build`.quiet();
	await $`docker compose --env-file security-disabled-env -f ./docker-compose-client-test-ollama.yml up --attach shabti-client`;
	await $`docker compose --env-file security-disabled-env -f ./docker-compose-client-test-ollama.yml stop`.quiet();
}
