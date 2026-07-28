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

export const keycloakExists = async () =>
	Promise.all([
		dockerItemExists("keycloak", "container"),
		dockerItemExists("postgres", "container"),
		dockerItemExists("shabti_postgres_data", "volume"),
	]).then((res) => res.every((value) => value));
