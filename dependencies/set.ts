/**
 * Sets one third party dependency to one exact version everywhere the repo pins it, then regenerates
 * whichever lockfiles that invalidated.
 *
 * bun ./dependencies/set.ts <name> <version> [--ecosystem <python|node|docker>] [--tag] [--no-lock]
 *
 * The version is never compared against the one already pinned: moving backwards out of a bad release is
 * as legitimate as moving forwards, so the only question asked is whether the version exists. That check
 * is against the registry's whole version list rather than a probe for the one version, which is what
 * lets `1.7` be accepted for `1.7.0` - the same version under PEP 440 - while the canonical spelling is
 * what gets written, and what lets a miss suggest what was meant instead.
 */

import { Command, Option } from "commander";
import semver from "semver";
import { normalise } from "../versioning/manifest";
import { type Registry, registry, unsupported } from "./catalogue";
import { type Options, client } from "./http";
import { type Runner, commandFor, lockActionsFor, regenerate } from "./lock";
import { compare, parse } from "./pep440";
import { group, readPins } from "./read";
import { applyEdits, plannedEdits } from "./rewrite";
import {
	ECOSYSTEMS,
	type Catalogue,
	type Dependency,
	type Ecosystem,
	type Release,
} from "./types";

export type Result = {
	name: string;
	ecosystem: Ecosystem;
	/** the versions that were pinned before, which may be more than one if the files disagreed */
	from: string[];
	to: string;
	files: string[];
	locked: string[];
	warnings: string[];
};

/** the dependency this name refers to, refusing rather than guessing when it refers to more than one */
export const find = (
	dependencies: Dependency[],
	name: string,
	ecosystem?: Ecosystem,
) => {
	const wanted = name.toLowerCase();
	const matches = dependencies.filter(
		(dependency) =>
			(!ecosystem || dependency.ecosystem === ecosystem) &&
			(dependency.id === name ||
				dependency.name === name ||
				dependency.id.toLowerCase() === wanted ||
				(dependency.ecosystem === "python" &&
					dependency.id === normalise(name))),
	);
	if (!matches.length) throw new Error(`nothing in this repo pins ${name}`);
	if (matches.length > 1)
		throw new Error(
			`${name} is pinned in more than one ecosystem (${matches
				.map((match) => match.ecosystem)
				.join(", ")}), so pass --ecosystem`,
		);
	return matches[0] as Dependency;
};

const distance = (a: string, b: string) => {
	let previous = Array.from({ length: b.length + 1 }, (_, index) => index);
	for (let i = 1; i <= a.length; i++) {
		const row = [i];
		for (let j = 1; j <= b.length; j++)
			row[j] = Math.min(
				(previous[j] as number) + 1,
				(row[j - 1] as number) + 1,
				(previous[j - 1] as number) + (a[i - 1] === b[j - 1] ? 0 : 1),
			);
		previous = row;
	}
	return previous[b.length] as number;
};

/** the same version however it was spelled, since 1.7 and 1.7.0 are one version under PEP 440 */
const matching = (
	catalogue: Catalogue,
	ecosystem: Ecosystem,
	requested: string,
): Release | undefined => {
	const exact = catalogue.releases.find(
		(release) => release.version === requested || release.raw === requested,
	);
	if (exact) return exact;
	if (ecosystem === "node") {
		const valid = semver.valid(requested);
		return valid
			? catalogue.releases.find((release) => release.version === valid)
			: undefined;
	}
	const wanted = parse(requested);
	if (!wanted) return undefined;
	return catalogue.releases.find((release) => {
		const have = parse(release.version);
		return have && compare(have, wanted) === 0;
	});
};

const suggestions = (catalogue: Catalogue, requested: string) =>
	[
		...new Set([
			...catalogue.releases
				.map((release) => release.version)
				.sort((a, b) => distance(a, requested) - distance(b, requested))
				.slice(0, 3),
			...(catalogue.latestStable ? [catalogue.latestStable.version] : []),
		]),
	].slice(0, 4);

export const set = async ({
	repoDir,
	name,
	version,
	ecosystem,
	literalTag,
	lock = true,
	registry: injected,
	run,
	...options
}: Options & {
	repoDir: string;
	name: string;
	version: string;
	ecosystem?: Ecosystem;
	literalTag?: boolean;
	lock?: boolean;
	registry?: Registry;
	run?: Runner;
}): Promise<Result> => {
	const dependency = find(group(await readPins(repoDir)), name, ecosystem);
	const warnings: string[] = [];
	let resolved = version;

	// a tag with no version in it has nothing to validate against, so --tag is taken on trust
	if (literalTag)
		warnings.push(`wrote the tag ${version} without checking it exists`);
	else {
		const reason = unsupported(dependency);
		if (reason) throw new Error(`cannot set ${dependency.name}: ${reason}`);
		const look =
			injected ?? registry(client(options), { resolveLatest: false });
		// deliberately not caught: refusing to write is the safe failure, unlike in the report
		const catalogue = await look(dependency);
		const release = matching(catalogue, dependency.ecosystem, version);
		if (!release)
			throw new Error(
				`${dependency.name} ${version} is not published; did you mean ${suggestions(catalogue, version).join(", ")}?`,
			);
		if (release.withdrawn)
			warnings.push(`${release.version} is ${release.withdrawn}`);
		// the registry's own spelling, so the manifest gets the canonical one
		resolved = release.version;
	}

	const edits = plannedEdits(dependency.occurrences, resolved, { literalTag });
	const files = await applyEdits(repoDir, edits);
	const actions = await lockActionsFor(repoDir, files);
	const locked = lock
		? await regenerate(repoDir, actions, run ? { run } : {})
		: actions.map(commandFor);
	if (!lock && actions.length)
		warnings.push(`did not run: ${actions.map(commandFor).join(", ")}`);

	return {
		name: dependency.name,
		ecosystem: dependency.ecosystem,
		from: dependency.versions,
		to: resolved,
		files,
		locked,
		warnings,
	};
};

if (import.meta.main) {
	const command = new Command()
		.argument("<name>", "the dependency as the manifests name it")
		.argument("<version>", "the version to pin it to, newer or older")
		.addOption(
			new Option(
				"--ecosystem <ecosystem>",
				"which one, when the same name is pinned in more than one",
			).choices([...ECOSYSTEMS]),
		)
		.option(
			"--tag",
			"write the version as the whole image tag, for a tag with no version to substitute into",
		)
		.option("--no-lock", "rewrite the pins but do not regenerate any lockfile")
		.parse();
	const [name, version] = command.args;
	const options = command.opts();

	const result = await set({
		repoDir: process.cwd(),
		name: name as string,
		version: version as string,
		ecosystem: options.ecosystem,
		literalTag: options.tag,
		lock: options.lock,
	});
	console.log(JSON.stringify(result));
	for (const warning of result.warnings) console.error(warning);
}
