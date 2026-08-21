import path from "node:path";
import { git, run } from "./git";
import { declaredVersion } from "./manifest";

const NODE = "package.json";
/** where a precise version of one of our packages can be named */
const PINNED_IN = /^(package\.json|pyproject\.toml|requirements[\w.-]*\.txt)$/;

/** the same reference manifest.ts reads, split so only the value is replaced */
const VERSION_LINE = /^(version\s*=\s*")([^"]+)/m;

/**
 * Puts a version into a package's manifest, returning the file it changed. Refuses unless the manifest
 * still declares `expected`: the versions are planned before anything is written, so anything else means
 * the tree moved underneath the plan.
 */
export const writeVersion = async (
	repoDir: string,
	packageDir: string,
	expected: string,
	next: string,
) => {
	const { manifest, type, version } = await declaredVersion(
		repoDir,
		packageDir,
	);
	if (version !== expected)
		throw new Error(`${manifest} declares ${version}, expected ${expected}`);
	if (type === "node")
		// bun keeps the tab indentation and the key order, and must neither commit nor tag
		await run(["bun", "pm", "version", next, "--no-git-tag-version"], {
			cwd: path.join(repoDir, packageDir),
		});
	else {
		// written by us rather than by uv, which would lock, and the containers can only lock in Docker
		const file = path.join(repoDir, manifest);
		const text = await Bun.file(file).text();
		await Bun.write(file, text.replace(VERSION_LINE, `$1${next}`));
	}
	return manifest;
};

const escape = (value: string) => value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");

/** matches the name however its separators and case are spelled, as PEP 503 allows */
const namePattern = (name: string) =>
	name
		.toLowerCase()
		.replace(/[-_.]+/g, "-")
		.split("-")
		.map(escape)
		.join("[-_.]+");

/**
 * A precise pin only: `"<name>": "0.1.0"` for node, where requiring a leading digit skips `workspace:*`
 * and every range operator, and `<name>==0.1.0` for python, which covers dependency arrays, dependency
 * groups and requirements lines alike.
 */
const pinPattern = (file: string, name: string) =>
	path.posix.basename(file) === NODE
		? new RegExp(`("${namePattern(name)}"\\s*:\\s*")(\\d[^"]*)`, "gi")
		: new RegExp(
				// the lookbehind keeps a short name from matching the tail of a longer one
				`(?<![\\w.-])(${namePattern(name)}(?:\\[[^\\]]*\\])?\\s*==\\s*)([\\w.!+*-]+)`,
				"gi",
			);

type Pinned = { name: string; current: string; next: string };

const repinned = (file: string, text: string, bump: Pinned) =>
	text.replace(
		pinPattern(file, bump.name),
		(_match, prefix: string, value: string) => {
			if (value !== bump.current)
				throw new Error(
					`${file} pins ${bump.name} at ${value}, but it declares ${bump.current}`,
				);
			return `${prefix}${bump.next}`;
		},
	);

/**
 * Rewrites every precise pin naming a bumped package, returning the files it changed. The files to check
 * come from git rather than from the packages themselves, so a pin in a file this tool knows nothing about
 * is still found. Lockfiles are deliberately not among them: uv.lock is regenerated in Docker, bun.lock by
 * the caller.
 *
 * A pin that names a version other than the one its package declares throws, and nothing is written until
 * every file has been checked, so a drifted pin leaves the tree untouched.
 */
export const rewritePins = async (repoDir: string, bumps: Pinned[]) => {
	if (!bumps.length) return [];
	const { stdout } = await git(repoDir)(
		"ls-files",
		"--cached",
		"--others",
		"--exclude-standard",
	);
	const files = stdout
		.split("\n")
		.map((file) => file.trim())
		.filter((file) => PINNED_IN.test(path.posix.basename(file)));

	const writes: [string, string][] = [];
	for (const file of files) {
		const original = await Bun.file(path.join(repoDir, file)).text();
		const rewritten = bumps.reduce(
			(text, bump) => repinned(file, text, bump),
			original,
		);
		if (rewritten !== original) writes.push([file, rewritten]);
	}
	for (const [file, text] of writes)
		await Bun.write(path.join(repoDir, file), text);
	return writes.map(([file]) => file);
};
