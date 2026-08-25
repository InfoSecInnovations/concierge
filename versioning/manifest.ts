import path from "node:path";

const NODE = "package.json";
const PYTHON = "pyproject.toml";

export const NODE_DEPENDENCIES = [
	"dependencies",
	"devDependencies",
	"peerDependencies",
	"optionalDependencies",
];

/**
 * The manifest a package directory declares its version in, as a posix path relative to the repo root so
 * it can be handed straight to git. package.json wins where both exist: only the repo root has both, and
 * its version lives there.
 */
export const manifestIn = async (repoDir: string, packageDir: string) => {
	for (const name of [NODE, PYTHON]) {
		const file = path.posix.join(packageDir, name);
		if (await Bun.file(path.join(repoDir, file)).exists()) return file;
	}
	throw new Error(`no ${NODE} or ${PYTHON} in ${packageDir}`);
};

/** which ecosystem a manifest belongs to */
export const typeIn = (file: string) => {
	switch (path.posix.basename(file)) {
		case NODE:
			return "node" as const;
		case PYTHON:
			return "python" as const;
		default:
			throw new Error(`${file} is not a ${NODE} or a ${PYTHON}`);
	}
};

const table = (value: unknown) =>
	value && typeof value === "object" ? (value as Record<string, unknown>) : {};

/** the string entries of an array, so a `{ include-group = ... }` dependency group table is skipped */
const strings = (value: unknown) =>
	Array.isArray(value)
		? value.filter((entry): entry is string => typeof entry === "string")
		: [];

/** parsing the working tree, so unreadable text is a failure rather than an answer */
const parsed = (file: string, text: string) => {
	try {
		return table(
			typeIn(file) === "node" ? JSON.parse(text) : Bun.TOML.parse(text),
		);
	} catch (error) {
		throw new Error(`could not parse ${file}: ${error}`);
	}
};

/**
 * The version a manifest declares, or null if it declares none or does not parse. Null rather than a
 * throw because a manifest somewhere back in history being unreadable is an answer - that commit is not
 * the one being looked for - not a failure.
 */
export const versionIn = (file: string, text: string): string | null => {
	switch (typeIn(file)) {
		case "node":
			try {
				return JSON.parse(text).version ?? null;
			} catch {
				return null;
			}
		case "python":
			// the first top level `version` line, i.e. [project]'s, which is the same assumption
			// .github/actions/get_pyproject_version makes with `grep -m 1 '^version'`
			return /^version\s*=\s*"([^"]+)"/m.exec(text)?.[1] ?? null;
	}
};

/** the manifest a package declares its version in, its ecosystem, and that version */
export const declaredVersion = async (repoDir: string, packageDir: string) => {
	const manifest = await manifestIn(repoDir, packageDir);
	const text = await Bun.file(path.join(repoDir, manifest)).text();
	const version = versionIn(manifest, text);
	if (!version) throw new Error(`no version declared in ${manifest}`);
	return { manifest, type: typeIn(manifest), version };
};

/** the distribution name a manifest declares, or null if it declares none */
export const nameIn = (file: string, text: string): string | null => {
	const manifest = parsed(file, text);
	const declared =
		typeIn(file) === "node" ? manifest.name : table(manifest.project).name;
	return typeof declared === "string" ? declared : null;
};

/** PEP 503 normalisation: the one spelling of a name two manifests can be compared by */
export const normalise = (name: string) =>
	name.toLowerCase().replace(/[-_.]+/g, "-");

/** the leading name of a PEP 508 requirement, dropping extras, specifiers and markers */
export const requirementName = (requirement: string) =>
	/^[A-Za-z0-9][A-Za-z0-9._-]*/.exec(requirement.trim())?.[0];

/** where a build requirement is declared, which is a dependency of the build and not of the project */
const BUILD_REQUIRES = "build-system.requires";

/**
 * Every requirement a pyproject declares, specifiers intact, each with the table it came from. Build
 * requirements are in the list because hatchling is as much a third party dependency as anything else;
 * the internal dependency graph filters them back out, since nothing builds one of our packages.
 */
export const requirementsIn = (file: string, text: string) => {
	const manifest = parsed(file, text);
	const project = table(manifest.project);
	const lists: [string, unknown][] = [
		["project.dependencies", project.dependencies],
		...Object.entries(table(project["optional-dependencies"])).map(
			([extra, list]): [string, unknown] => [
				`project.optional-dependencies.${extra}`,
				list,
			],
		),
		...Object.entries(table(manifest["dependency-groups"])).map(
			([group, list]): [string, unknown] => [
				`dependency-groups.${group}`,
				list,
			],
		),
		[BUILD_REQUIRES, table(manifest["build-system"]).requires],
	];
	return lists.flatMap(([location, list]) =>
		strings(list).map((requirement) => ({ requirement, location })),
	);
};

/** every dependency a manifest declares, external ones included, from every kind of dependency list */
export const dependencyNamesIn = (file: string, text: string): string[] => {
	if (typeIn(file) === "node")
		return NODE_DEPENDENCIES.flatMap((key) =>
			Object.keys(table(parsed(file, text)[key])),
		);
	return requirementsIn(file, text)
		.filter(({ location }) => location !== BUILD_REQUIRES)
		.map(({ requirement }) => requirementName(requirement))
		.filter((name): name is string => !!name);
};
