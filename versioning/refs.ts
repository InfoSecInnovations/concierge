import type { VersionRef } from "./registry";
import { absolute } from "./repo";

const escape = (value: string) => value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");

/**
 * Every reference is matched by a regex with a `value` group holding the version, and edits replace
 * only that group, so the rest of the file survives byte for byte. That matters: the two
 * requirements.txt files have no trailing newline and both the root and configurator package.json
 * keep `version` as their last key, neither of which a parse and re-serialise round trip would
 * reliably preserve.
 */
const matcher = (ref: VersionRef) => {
	switch (ref.kind) {
		case "pyprojectVersion":
			// the first `version` line at the top level, i.e. [project]'s, which is the same
			// assumption .github/actions/get_pyproject_version makes with `grep -m 1 '^version'`
			return { pattern: /^version\s*=\s*"(?<value>[^"]+)"/m, all: false };
		case "packageJsonVersion":
			// anchored to a single tab so nested "version" keys can't match
			return { pattern: /^\t"version"\s*:\s*"(?<value>[^"]+)"/m, all: false };
		case "requirementsPin":
			// $ under /m also matches the end of the file, so an un-newlined last line still matches
			return {
				pattern: new RegExp(
					`^${escape(ref.pkg)}\\s*==\\s*(?<value>\\S+)$`,
					"gm",
				),
				all: true,
			};
		case "pyprojectDepPin":
			// a package can be pinned in both [project] dependencies and a dependency group
			return {
				pattern: new RegExp(
					`(?<quote>["'])${escape(ref.pkg)}\\s*==\\s*(?<value>[^"']+)\\k<quote>`,
					"g",
				),
				all: true,
			};
		case "uvLockSelf":
			return {
				pattern: new RegExp(
					`^\\[\\[package\\]\\]\\nname = "${escape(ref.pkg)}"\\nversion = "(?<value>[^"]+)"`,
					"m",
				),
				all: false,
			};
	}
};

const describe = (ref: VersionRef) =>
	"pkg" in ref ? `${ref.file} (${ref.pkg})` : ref.file;

const valuesIn = (ref: VersionRef, text: string) => {
	const { pattern, all } = matcher(ref);
	const matches = all
		? [...text.matchAll(pattern)]
		: [pattern.exec(text)].filter((match) => !!match);
	return matches.map((match) => match.groups?.value as string);
};

/** the version currently declared in a file */
export const readRef = async (ref: VersionRef) => {
	const text = await Bun.file(absolute(ref.file)).text();
	const values = valuesIn(ref, text);
	if (!values.length)
		throw new Error(`no version reference found in ${describe(ref)}`);
	const unique = [...new Set(values)];
	if (unique.length > 1)
		throw new Error(
			`${describe(ref)} declares more than one version: ${unique.join(", ")}`,
		);
	return unique[0];
};

const replaceLast = (text: string, find: string, replacement: string) => {
	const at = text.lastIndexOf(find);
	return text.slice(0, at) + replacement + text.slice(at + find.length);
};

/**
 * The file text with the reference moved from `expected` to `next`. Throws if the version it is
 * about to overwrite is not the one the component declares, which is what catches a hand edited pin
 * that has drifted, a regex that has matched the wrong line, and a pin added to a file without
 * being added to the registry.
 */
export const applyRef = (
	ref: VersionRef,
	expected: string,
	next: string,
	text: string,
) => {
	const { pattern, all } = matcher(ref);
	const values = valuesIn(ref, text);
	if (!values.length)
		throw new Error(`no version reference found in ${describe(ref)}`);
	if (!all && values.length > 1)
		throw new Error(
			`expected a single version reference in ${describe(ref)}, found ${values.length}`,
		);
	for (const value of values) {
		if (value !== expected)
			throw new Error(
				`version reference mismatch: ${describe(ref)} expects ${expected}, found ${value}`,
			);
	}
	// the regex is rebuilt above, so its lastIndex is clean for replace()
	return text.replace(pattern, (match) => replaceLast(match, expected, next));
};

/**
 * Loads files on demand and holds their edits in memory, so a failure part way through planning a
 * release leaves the working tree untouched.
 */
export class EditPlan {
	private texts = new Map<string, string>();
	readonly descriptions: string[] = [];

	async edit(ref: VersionRef, expected: string, next: string) {
		const text =
			this.texts.get(ref.file) ?? (await Bun.file(absolute(ref.file)).text());
		this.texts.set(ref.file, applyRef(ref, expected, next, text));
		this.descriptions.push(`${describe(ref)}: ${expected} -> ${next}`);
	}

	get files() {
		return [...this.texts.keys()];
	}

	async write() {
		for (const [file, text] of this.texts)
			await Bun.write(absolute(file), text);
		return this.files;
	}
}
