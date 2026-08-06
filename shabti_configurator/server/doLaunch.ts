import { $ } from "bun";
import * as envfile from "envfile";
import getEnvPath from "./getEnvPath";
import logMessage from "./logMessage";
import removeAllContainers from "./removeAllContainers";

export default async function* (
	options: FormData,
	state: { watchProcess?: Bun.Subprocess },
) {
	const envs = envfile.parse(await Bun.file(getEnvPath()).text());
	const isLocal = envs.SHABTI_LOCAL_VERSION == "True";
	if (options.get("environment") == "stop") {
		if (!isLocal) {
			yield logMessage("Stopping Shabti Docker Compose configuration...");
			// this removes the containers and the network but leaves the volumes alone, so no
			// models or ingested documents are lost
			await $`docker compose -f ./docker_compose/docker-compose.yml down`;
			return;
		}
		yield logMessage("Stopping local Docker development configuration...");
		// the containers can also be running from the devcontainer or a test run, in which case
		// there's no watch process of ours to stop
		if (state.watchProcess) {
			state.watchProcess.kill("SIGINT");
			await state.watchProcess.exited;
			delete state.watchProcess;
		}
		await $`docker compose -f ./docker_compose/docker-compose-dev.yml stop`;
		return;
	}
	envs.SHABTI_COMPUTE = options.has("use_gpu") ? "cuda" : "cpu";
	yield logMessage(
		`Launching Shabti ${envs.SHABTI_COMPUTE == "cuda" ? "with" : "without"} GPU acceleration.`,
	);
	await removeAllContainers();
	await Bun.write(getEnvPath(), envfile.stringify(envs));
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
	} else {
		yield logMessage("Launching Shabti Docker Compose configuration...");
		await $`docker compose -f ./docker_compose/docker-compose.yml up -d`;
	}
}
