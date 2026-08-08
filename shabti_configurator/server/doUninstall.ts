import path from "node:path";
import { rm } from "node:fs/promises";
import { $ } from "bun";
import getEnvPath from "./getEnvPath";
import logMessage from "./logMessage";
import removeAllContainers from "./removeAllContainers";
import { getModelsIniPath } from "./writeModelsIni";

export default async function* (
	options: FormData,
	state: { watchProcess?: Bun.Subprocess },
) {
	// the development configuration runs in watch mode, so it would bring the containers back
	// up as soon as we removed them
	if (state.watchProcess) {
		yield logMessage("Stopping local Docker development configuration...");
		state.watchProcess.kill("SIGINT");
		await state.watchProcess.exited;
		delete state.watchProcess;
	}
	yield logMessage("Removing Shabti Docker containers...");
	await removeAllContainers();
	yield logMessage("Removing Shabti data volumes...");
	// after the containers because a volume still in use can't be removed, and forced so the
	// volumes a given configuration doesn't have (postgres without security, for instance) are
	// a no-op rather than an error
	await $`docker volume rm --force shabti_opensearch-data1 shabti_shabti-files shabti_postgres_data`;
	if (options.has("delete_models")) {
		yield logMessage("Removing downloaded language model files...");
		await $`docker volume rm --force shabti_llama-cpp-models`;
	}
	// the compose files name the default network, and removing the containers leaves it behind.
	// nothrow because unlike the removals above this errors when there's nothing to remove
	await $`docker network rm shabti`.nothrow().quiet();
	yield logMessage("Removing Shabti configuration...");
	// getCurrentVersion looks for the .env, so removing it is what makes the configurator treat
	// Shabti as no longer installed. We leave the compose files alone as a non dev-mode startup
	// re-extracts them from the bundled zip anyway.
	await rm(getEnvPath(), { force: true });
	// recursive because Docker creates a directory here if the containers were launched before
	// the file existed
	await rm(getModelsIniPath(), { force: true, recursive: true });
	await rm(path.resolve("self_signed_certificates"), {
		force: true,
		recursive: true,
	});
}
