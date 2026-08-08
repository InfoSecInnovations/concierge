import { $ } from "bun";
import logMessage from "./logMessage";
import removeAllContainers from "./removeAllContainers";

// brings the containers up from whatever is currently in the environment file. The containers
// are removed rather than restarted because port mappings and bind mounts are fixed when a
// container is created, so that's the only way a configuration change takes effect
export default async function* (
	isLocal: boolean,
	state: { watchProcess?: Bun.Subprocess },
) {
	await removeAllContainers();
	if (isLocal) {
		if (state.watchProcess) {
			yield logMessage(
				"Local Docker development configuration already running!",
			);
			return;
		}
		yield logMessage(
			"Building Docker image to run local code. This can take a while depending on your internet connection...",
		);
		await $`docker compose -f ./docker_compose/docker-compose-dev.yml build`;
		yield logMessage(
			"Launching Docker Compose configuration with local code...",
		);
		state.watchProcess = Bun.spawn([
			"docker",
			"compose",
			"-f",
			"./docker_compose/docker-compose-dev.yml",
			"up",
		]);
		return;
	}
	yield logMessage("Launching Shabti Docker Compose configuration...");
	await $`docker compose -f ./docker_compose/docker-compose.yml up -d`;
}
