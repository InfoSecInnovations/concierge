import { $ } from "bun";

export const dockerItemExists = async (itemName: string, itemType: string) => {
	try {
		const data = await $`docker inspect --type=${itemType} ${itemName}`.json();
		// depending on the item type the compose project is in a different place
		if (data[0]?.["Labels"]?.["com.docker.compose.project"] == "shabti")
			return true;
		if (
			data[0]?.["Config"]?.["Labels"]?.["com.docker.compose.project"] ==
			"shabti"
		)
			return true;
		return false;
	} catch {
		return false;
	}
};

// quiet unlike the above because this runs for every expected container on each page render,
// so a stopped installation would otherwise fill the console with "No such object"
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

export const keycloakExists = async () =>
	Promise.all([
		dockerItemExists("keycloak", "container"),
		dockerItemExists("postgres", "container"),
		dockerItemExists("shabti_postgres_data", "volume"),
	]).then((res) => res.every((value) => value));
