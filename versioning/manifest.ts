import path from "node:path";

const NODE = "package.json";
const PYTHON = "pyproject.toml";

const NODE_DEPENDENCIES = [
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

/** the distribution name a manifest declares, or null if it declares none */
export const nameIn = (file: string, text: string): string | null => {
	const manifest = parsed(file, text);
	const declared =
		typeIn(file) === "node" ? manifest.name : table(manifest.project).name;
	return typeof declared === "string" ? declared : null;
};

/** the leading name of a PEP 508 requirement, dropping extras, specifiers and markers */
const requirementName = (requirement: string) =>
	/^[A-Za-z0-9][A-Za-z0-9._-]*/.exec(requirement.trim())?.[0];

/** every dependency a manifest declares, external ones included, from every kind of dependency list */
export const dependencyNamesIn = (file: string, text: string): string[] => {
	const manifest = parsed(file, text);
	if (typeIn(file) === "node")
		return NODE_DEPENDENCIES.flatMap((key) =>
			Object.keys(table(manifest[key])),
		);
	const project = table(manifest.project);
	return [
		project.dependencies,
		...Object.values(table(project["optional-dependencies"])),
		...Object.values(table(manifest["dependency-groups"])),
	]
		.flatMap(strings)
		.map(requirementName)
		.filter((name): name is string => !!name);
};
