import { dependents, readPackages } from "./deps";
import { changedSince } from "./history";
import { type Preid, type ReleaseType, nextVersion } from "./versions";

export type Bump = {
	path: string;
	manifest: string;
	type: "node" | "python";
	name: string;
	current: string;
	next: string;
	/** whether the package's own directory changed, or a dependency's bump pulled it in */
	reason: "changed" | "dependency";
};

/**
 * Every package a release touches, with the version each will be written to. A package is touched when its
 * own directory changed since the version it declares was set, or when something it depends on is being
 * bumped: a local dependency leaves no diff behind but does change the bundled output.
 *
 * Nothing is written, so the whole release can be rejected before it starts, and every refusal is reported
 * at once rather than one per run. The root is not one of the paths - only components are published - so
 * the caller decides the root's own bump from the length of this list.
 */
export const planBumps = async (
	repoDir: string,
	paths: string[],
	releaseType: ReleaseType,
	preid?: Preid,
): Promise<Bump[]> => {
	const packages = await readPackages(repoDir, paths);
	const diffs = await Promise.all(
		packages.map(async (pkg) => ({
			path: pkg.path,
			...(await changedSince(repoDir, pkg.path)),
		})),
	);

	// the map is both the answer and the bookmark that stops a dependency cycle from looping
	const affected = new Map<string, Bump["reason"]>(
		diffs.filter(({ changed }) => changed).map(({ path }) => [path, "changed"]),
	);
	// appending to the array being walked is the breadth first pass over the dependency links
	const queue = [...affected.keys()];
	for (const path of queue)
		for (const dependent of dependents(packages, path))
			if (!affected.has(dependent)) {
				affected.set(dependent, "dependency");
				queue.push(dependent);
			}

	const touched = packages.filter((pkg) => affected.has(pkg.path));
	const computed = await Promise.allSettled(
		touched.map((pkg) => nextVersion(repoDir, pkg.path, releaseType, preid)),
	);
	const refused = touched.flatMap((pkg, index) => {
		const result = computed[index];
		return result.status === "rejected"
			? [`${pkg.path}: ${result.reason.message}`]
			: [];
	});
	if (refused.length)
		throw new Error(`cannot ${releaseType}: ${refused.join("; ")}`);

	return touched.flatMap(({ path, manifest, type, name }, index) => {
		const result = computed[index];
		if (result.status === "rejected") return [];
		return [
			{
				path,
				manifest,
				type,
				name,
				...result.value,
				reason: affected.get(path) as Bump["reason"],
			},
		];
	});
};
