import path from "node:path";
import * as envfile from "envfile";
import getEnvPath from "./getEnvPath";

export default async () => {
	const envFile = Bun.file(getEnvPath());
	if (
		await Promise.all([
			envFile.exists(),
			Bun.file(path.join("docker_compose", "docker-compose.yml")).exists(),
		]).then((res) => res.every((exists) => exists))
	) {
		const envs = envfile.parse(await envFile.text());
		return envs.SHABTI_VERSION as string | undefined;
		// this isn't exhaustive but should in most cases be sufficient to confirm that the user has an existing configuration
	}
	return undefined;
};
