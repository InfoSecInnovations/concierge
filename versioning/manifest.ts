import path from "node:path";

const NODE = "package.json";
const PYTHON = "pyproject.toml";

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

/**
 * The version a manifest declares, or null if it declares none or does not parse. Null rather than a
 * throw because a manifest somewhere back in history being unreadable is an answer - that commit is not
 * the one being looked for - not a failure.
 */
export const versionIn = (file: string, text: string): string | null => {
	switch (path.posix.basename(file)) {
		case NODE:
			try {
				return JSON.parse(text).version ?? null;
			} catch {
				return null;
			}
		case PYTHON:
			// the first top level `version` line, i.e. [project]'s, which is the same assumption
			// .github/actions/get_pyproject_version makes with `grep -m 1 '^version'`
			return /^version\s*=\s*"([^"]+)"/m.exec(text)?.[1] ?? null;
		default:
			throw new Error(`${file} is not a ${NODE} or a ${PYTHON}`);
	}
};
