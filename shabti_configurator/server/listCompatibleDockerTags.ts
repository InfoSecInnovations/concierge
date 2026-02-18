import minimumVersion from "../minimumVersion";
import semver from "semver";

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
	tags.push("0.7.0");
	tags.push("0.8.0");
	tags.push("0.7.0-alpha.2");
	tags.push("0.8.0-alpha.2");
	tags.push("0.8.0-alpha.2-cuda");
	const filteredTags = [
		...new Set(tags.map((tag) => tag.replace("-cuda", ""))),
	]; // filter out the suffixes as we will apply those using the GPU enabled option
	return filteredTags
		.filter(
			(tag) =>
				semver.compare(
					semver.coerce(tag, { loose: true }) || "",
					minimumVersion,
					true,
				) >= 0,
		)
		.sort((a, b) => {
			// put "invalid" versions the lowest, these are probably using the old Python versioning
			if (semver.valid(a, true) && !semver.valid(b, true)) return -1;
			if (semver.valid(b, true) && !semver.valid(a, true)) return 1;
			// sort prerelease versions after "stable"
			try {
				if (
					semver.prerelease(a, true)?.length &&
					!semver.prerelease(b, true)?.length
				)
					return 1;
				if (
					semver.prerelease(b, true)?.length &&
					!semver.prerelease(a, true)?.length
				)
					return -1;
			} catch {}
			return semver.rcompare(
				semver.coerce(a, { loose: true }) || "",
				semver.coerce(b, { loose: true }) || "",
				true,
			);
		}); // sort by highest first
};
