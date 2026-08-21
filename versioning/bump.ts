/**
 * Bumps every component a release touches, along with the root, and rewrites every pin that names one of
 * them. Nothing is written until every version has been worked out, so a release that cannot be applied is
 * refused before it starts.
 *
 * bun ./versioning/bump.ts --release-type <type> [--preid <alpha|beta|rc>] [--dry-run] --paths <path...>
 *
 * The root is not one of the paths: it always moves by one increment when anything else does. Generated
 * files are left to the caller - the workflow regenerates the lockfiles and shabti-components.json between
 * the bump and the commit - so the reported files are only the ones written here.
 */

import { appendFile } from "node:fs/promises";
import { Command, Option } from "commander";
import { readPackages } from "./deps";
import { planBumps } from "./plan";
import {
	PREIDS,
	type Preid,
	RELEASE_TYPES,
	type ReleaseType,
	nextVersion,
} from "./versions";
import { rewritePins, writeVersion } from "./write";

const ROOT = ".";

export type Report = {
	root: string;
	bumps: { path: string; name: string; current: string; next: string }[];
	files: string[];
};

export const bump = async ({
	repoDir,
	paths,
	releaseType,
	preid,
	dryRun,
}: {
	repoDir: string;
	paths: string[];
	releaseType: ReleaseType;
	preid?: Preid;
	dryRun?: boolean;
}): Promise<Report> => {
	const bumps = await planBumps(repoDir, paths, releaseType, preid);
	// a release promotes the root prerelease whether or not any component moved, anything else has nothing
	// to do
	if (!bumps.length && releaseType !== "release")
		throw new Error(`nothing changed, so there is nothing to ${releaseType}`);

	const [rootPackage] = await readPackages(repoDir, [ROOT]);
	const root = {
		...rootPackage,
		...(await nextVersion(repoDir, ROOT, releaseType, preid)),
	};
	const report = {
		root: root.next,
		bumps: bumps.map(({ path, name, current, next }) => ({
			path,
			name,
			current,
			next,
		})),
	};
	if (dryRun) return { ...report, files: [] };

	const written: string[] = [];
	for (const { path, current, next } of [...bumps, root])
		written.push(await writeVersion(repoDir, path, current, next));
	// the root is in the list too: nothing pins it today, but the rewriter is meant to stay generic
	const pinned = await rewritePins(repoDir, [...bumps, root]);
	return { ...report, files: [...new Set([...written, ...pinned])].sort() };
};

/** what the workflow steps read: the version to tag, whether anything was written, and what to stage */
const outputs = (report: Report) =>
	[
		`root-version=${report.root}`,
		`bumped=${report.files.length > 0}`,
		`touched-files<<FILES\n${report.files.join("\n")}\nFILES`,
	].join("\n");

if (import.meta.main) {
	const command = new Command()
		.addOption(
			new Option("--release-type <type>", "how far to move the versions")
				.makeOptionMandatory()
				.choices([...RELEASE_TYPES]),
		)
		.addOption(
			new Option(
				"--preid <preid>",
				"prerelease stage, defaulting to the existing one or alpha",
			).choices([...PREIDS]),
		)
		.option("--dry-run", "work out the versions without writing anything")
		.requiredOption(
			"--paths <paths...>",
			"the package directories to check, excluding the root",
		)
		.parse();
	const options = command.opts();

	const report = await bump({
		repoDir: process.cwd(),
		paths: options.paths,
		releaseType: options.releaseType,
		preid: options.preid,
		dryRun: options.dryRun,
	});
	console.log(JSON.stringify(report));
	if (process.env.GITHUB_OUTPUT)
		await appendFile(process.env.GITHUB_OUTPUT, `${outputs(report)}\n`);
}
