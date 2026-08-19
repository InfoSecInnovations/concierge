import path from "node:path";
import { dependencyNamesIn, manifestIn, nameIn, typeIn } from "./manifest";

export type PackageInfo = {
	/** the --paths entry */
	path: string;
	/** posix, relative to the repo root */
	manifest: string;
	type: "node" | "python";
	/** distribution name */
	name: string;
	/** the paths of the listed packages it declares a dependency on */
	dependsOn: string[];
};

/** PEP 503 normalisation, which also forgives shabti_util for shabti-util */
const key = (type: string, name: string) =>
	`${type}:${name.toLowerCase().replace(/[-_.]+/g, "-")}`;

/**
 * Every listed package with its internal dependency edges resolved, read from the manifests rather than
 * inferred from diffs: since the containers name their internal dependencies without a version and resolve
 * them by path, bumping one of those leaves nothing inside the container's directory for a diff to find.
 *
 * A dependency only resolves within its own ecosystem, because the same code ships twice under names that
 * are otherwise easy to confuse - shabti-api-client on PyPI, @infosecinnovations/shabti-api-client on npm.
 */
export const readPackages = async (
	repoDir: string,
	paths: string[],
): Promise<PackageInfo[]> => {
	const read = await Promise.all(
		paths.map(async (packagePath) => {
			const manifest = await manifestIn(repoDir, packagePath);
			const text = await Bun.file(path.join(repoDir, manifest)).text();
			const name = nameIn(manifest, text);
			if (!name) throw new Error(`no name declared in ${manifest}`);
			return {
				path: packagePath,
				manifest,
				type: typeIn(manifest),
				name,
				declared: dependencyNamesIn(manifest, text),
			};
		}),
	);
	const byName = new Map(
		read.map((pkg) => [key(pkg.type, pkg.name), pkg.path]),
	);
	return read.map(({ declared, ...pkg }) => ({
		...pkg,
		dependsOn: declared
			.map((name) => byName.get(key(pkg.type, name)))
			.filter(
				(dependency): dependency is string =>
					!!dependency && dependency !== pkg.path,
			),
	}));
};

/** the paths whose manifests name the package at this path. One hop: the caller's cascade loops */
export const dependents = (packages: PackageInfo[], packagePath: string) => {
	if (!packages.some((pkg) => pkg.path === packagePath))
		throw new Error(`${packagePath} is not one of the packages being read`);
	return packages
		.filter((pkg) => pkg.dependsOn.includes(packagePath))
		.map((pkg) => pkg.path);
};
