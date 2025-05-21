import { $ } from "bun";

export default async () => {
	try {
		await $`docker info`.quiet();
		return true;
	} catch {
		return false;
	}
};
