/**
 * What npm has published for a package.
 *
 * Read with the abbreviated metadata header, which is the same data minus the READMEs and per version
 * publisher records: hono is 719 KB abbreviated against 6.11 MB full. It still carries `dist-tags` and
 * the per version `deprecated` string, which is everything needed here.
 *
 * semver is the comparator on this side, and only on this side. It is already a root dependency and it
 * is the definition of ordering for npm, where PEP 440 is for PyPI and for container tags.
 */

import semver from "semver";
import type { Client } from "../http";
import { assemble, unreadableNote } from "../releases";
import type { Catalogue, Release } from "../types";

const ACCEPT = "application/vnd.npm.install-v1+json";

type Document = {
	"dist-tags"?: Record<string, string>;
	versions?: Record<string, { deprecated?: string } | undefined>;
};

export const npmCatalogue = async (
	name: string,
	client: Client,
	registry = "https://registry.npmjs.org",
): Promise<Catalogue> => {
	// the documented encoding for a scoped name, and it keeps the @ readable in an error message
	const response = await client.request(
		`${registry}/${name.replace("/", "%2F")}`,
		{ headers: { accept: ACCEPT } },
	);
	if (response.status === 404)
		throw new Error(`${name} is not published on npm`);
	if (!response.ok)
		throw new Error(`npm returned ${response.status} for ${name}`);

	const body = (await response.json()) as Document;
	const distTags = body["dist-tags"] ?? {};

	let unreadable = 0;
	const entries = Object.entries(body.versions ?? {}).flatMap(
		([version, meta]) => {
			if (!semver.valid(version)) {
				unreadable++;
				return [];
			}
			return [{ version, deprecated: meta?.deprecated }];
		},
	);

	const catalogue = assemble(
		entries,
		(a, b) => semver.compare(a.version, b.version),
		({ version, deprecated }): Release => ({
			version,
			prerelease: semver.prerelease(version) !== null,
			withdrawn: deprecated ? `deprecated: ${deprecated}` : undefined,
		}),
		unreadableNote(unreadable, "npm"),
	);

	const declared = distTags.latest;
	const tagged = declared
		? catalogue.releases.find(({ version }) => version === declared)
		: undefined;
	const notes = [...catalogue.notes];
	let latestStable = catalogue.latestStable;

	if (tagged?.prerelease)
		// verified live on @jsr/std__ini, which tags 1.0.0-rc.9 as latest
		notes.push(
			`the registry tags ${declared} as latest, which is a prerelease; the highest stable release is ${latestStable?.version ?? "none"}`,
		);
	else if (tagged && !tagged.withdrawn) {
		if (latestStable && latestStable.version !== tagged.version)
			notes.push(
				`the registry tags ${declared} as latest, but ${latestStable.version} is higher`,
			);
		// what `npm install` actually gives you is the answer, even when something higher exists
		latestStable = tagged;
	}

	// recomputed against the tag's answer rather than the highest version, so the two agree
	const newest = catalogue.releases
		.filter(({ prerelease, withdrawn }) => prerelease && !withdrawn)
		.at(-1);
	const latestPrerelease =
		newest &&
		(!latestStable ||
			catalogue.releases.indexOf(newest) >
				catalogue.releases.indexOf(latestStable))
			? newest
			: undefined;

	return { ...catalogue, latestStable, latestPrerelease, distTags, notes };
};
