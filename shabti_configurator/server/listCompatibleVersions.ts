import { Octokit } from "octokit";
import semver from "semver";
import packageJson from "../package.json";

export default async () => {
	const octokit = new Octokit();
	const releases = await octokit.paginate(octokit.rest.repos.listReleases, {
		owner: "InfoSecInnovations",
		repo: "shabti",
		per_page: 100,
		headers: {
			"X-GitHub-Api-Version": "2026-03-10",
		},
	});
	const componentsAssets = releases
		.map((release) =>
			release.assets.filter((asset) => asset.name == "shabti-components.json"),
		)
		.flat();
	const configuratorVersion = packageJson.version;
	return await Promise.all(
		componentsAssets.map((asset) =>
			fetch(asset.url, {
				headers: { Accept: "application/octet-stream" },
			}).then((res) => res.json() as any),
		),
	).then((releases) =>
		releases
			.filter((release) =>
				semver.gte(configuratorVersion, release.configuratorMinVersion),
			)
			.sort((a, b) => {
				// sort prerelease versions after "stable"
				try {
					if (
						semver.prerelease(a.version, true)?.length &&
						!semver.prerelease(b.version, true)?.length
					)
						return 1;
					if (
						semver.prerelease(b.version, true)?.length &&
						!semver.prerelease(a.version, true)?.length
					)
						return -1;
				} catch {}
				return semver.rcompare(
					semver.coerce(a.version, { loose: true }) || "",
					semver.coerce(b.version, { loose: true }) || "",
					true,
				); // sort by highest first
			})
			.map((release) => release.version),
	);
};
