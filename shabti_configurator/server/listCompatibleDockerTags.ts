import { Octokit } from "octokit";
import semver from "semver";
import packageJson from "../package.json";

//export default async () => {
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
const releaseData = await Promise.all(
	componentsAssets.map((asset) =>
		fetch(asset.url, { headers: { Accept: "application/octet-stream" } }).then(
			(res) => res.json() as any,
		),
	),
);
console.log(releaseData);
//};
