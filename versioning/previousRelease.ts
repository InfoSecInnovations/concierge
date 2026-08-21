/**
 * The release a release follows, by semver rather than by date: a fix release can be tagged after a
 * prerelease of the next version, so the newest tag is not necessarily the one whose assets carry forward.
 *
 * bun ./versioning/previousRelease.ts --prefix shabti-v --below 0.9.0
 */

import { Command } from "commander";
import semver from "semver";
import { git } from "./git";

export const previousRelease = async (
	repoDir: string,
	prefix: string,
	below: string,
) => {
	const { stdout } = await git(repoDir)("tag", "--list", `${prefix}*`);
	const [highest] = stdout
		.split("\n")
		.map((tag) => tag.trim().slice(prefix.length))
		.filter((version) => !!semver.valid(version) && semver.lt(version, below))
		.sort(semver.rcompare);
	return highest ? `${prefix}${highest}` : null;
};

if (import.meta.main) {
	const { prefix, below } = new Command()
		.requiredOption("--prefix <prefix>", "the release tag prefix")
		.requiredOption("--below <version>", "the version being released")
		.parse()
		.opts();
	// nothing at all when there is no earlier release, which the caller can treat as "the first one"
	console.log((await previousRelease(process.cwd(), prefix, below)) ?? "");
}
