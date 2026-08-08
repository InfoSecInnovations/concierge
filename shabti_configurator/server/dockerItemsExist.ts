import { $ } from "bun";

// quiet because this runs for every expected container on each page render, so a stopped
// installation would otherwise fill the console with "No such object"
export const containerIsRunning = async (containerName: string) => {
	try {
		const data = await $`docker container inspect ${containerName}`
			.quiet()
			.json();
		if (!data[0]?.["State"]?.["Running"]) return false;
		return (
			data[0]?.["Config"]?.["Labels"]?.["com.docker.compose.project"] ==
			"shabti"
		);
	} catch {
		return false;
	}
};
