import { $ } from "bun";
import * as envfile from "envfile";
import getEnvPath from "./getEnvPath";
import logMessage from "./logMessage";

export default async function* (options: FormData) {
	const environment = options.get("environment");
	const envs = envfile.parse(await Bun.file(getEnvPath()).text());
	envs.SHABTI_COMPUTE = options.has("use_gpu") ? "cuda" : "cpu";
	yield logMessage(
		`Launching Shabti ${envs.SHABTI_COMPUTE == "cuda" ? "with" : "without"} GPU acceleration.`,
	);
	await Bun.write(getEnvPath(), envfile.stringify(envs));

	if (environment == "local") {
		yield logMessage(
			"Building Docker image to run local code. This can take a while depending on your internet connection...",
		);
		await $`docker compose -f ./docker_compose/docker-compose-dev.yml build`;
		yield logMessage(
			"Launching Docker Compose configuration with local code...",
		);
		await $`docker compose -f ./docker_compose/docker-compose-dev.yml up -d --watch`;
	} else {
		yield logMessage("Launching Shabti Docker Compose configuration...");
		await $`docker compose -f ./docker_compose/docker-compose.yml up -d`;
	}
}
