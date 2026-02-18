import minimumVersion from "../minimumVersion";
import { semver } from "bun";

export default async () => {
	let next =
		"https://hub.docker.com/v2/namespaces/infosecinnovations/repositories/shabti/tags?page_size=100";
	const tags = [] as string[];
	while (next) {
		const response: any = await fetch(
			"https://hub.docker.com/v2/namespaces/infosecinnovations/repositories/shabti/tags?page_size=100",
		).then((res) => res.json());
		next = response.next;
		for (const tag of response.results) {
			tags.push(tag.name);
		}
	}
	return tags
		.filter((tag) => semver.order(tag, minimumVersion) >= 0)
		.sort((a, b) => semver.order(b, a)); // sort by highest first
};
