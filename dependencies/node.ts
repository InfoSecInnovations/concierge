/**
 * Reading the node pins out of a package.json.
 *
 * npm names are compared byte for byte here, unlike python's, where PEP 503 makes foo-bar and foo_bar
 * the same project. versioning/write.ts folds separators on both sides because the only names it ever
 * matches are our own; this reads arbitrary third party names, where folding would merge two different
 * packages.
 */

import semver from "semver";
import { NODE_DEPENDENCIES } from "../versioning/manifest";
import type { Pin, Precision } from "./types";

/** resolved by something other than a registry version, so there is no upstream to compare against */
const PROTOCOL =
	/^(workspace|file|link|portal|catalog|git|git\+[\w.+-]+|https?|github|gitlab|bitbucket):/;

export type Classification = {
	precision: Precision;
	version: string | null;
	/** for `npm:@jsr/std__ini` and `npm:foo@^1.2.3`, whose real name is not the key it is written under */
	alias?: { target: string; range: string };
};

/**
 * What a specifier is, or null when it names no registry version at all - a workspace link, a path, a
 * git URL. Those are out of scope rather than unpinned: there is nothing upstream to be behind.
 */
export const classify = (specifier: string): Classification | null => {
	const trimmed = specifier.trim();
	if (PROTOCOL.test(trimmed)) return null;
	if (trimmed.startsWith("npm:")) {
		const rest = trimmed.slice("npm:".length);
		// the target may be scoped, so the range splits at the last @ rather than the first
		const at = rest.lastIndexOf("@");
		const target = at > 0 ? rest.slice(0, at) : rest;
		const range = at > 0 ? rest.slice(at + 1) : "";
		return { precision: "alias", version: null, alias: { target, range } };
	}
	if (semver.valid(trimmed)) return { precision: "exact", version: trimmed };
	// catches "*", "", "^5", ">=1 <2" and every hyphen and x-range
	if (semver.validRange(trimmed)) return { precision: "range", version: null };
	// a dist-tag such as "latest": a real reference to whatever the registry currently points it at
	return { precision: "tag", version: null };
};

/**
 * The line a dependency is declared on. Found by searching for the quoted key, which is enough for
 * something only ever shown to a human, and 0 when it cannot be found at all.
 */
const lineOf = (text: string, name: string) => {
	const at = text.indexOf(`"${name}"`);
	return at < 0 ? 0 : text.slice(0, at).split("\n").length;
};

const table = (value: unknown) =>
	value && typeof value === "object" ? (value as Record<string, unknown>) : {};

/** every third party pin a package.json declares, from all four kinds of dependency field */
export const nodePins = (file: string, text: string): Pin[] => {
	let manifest: Record<string, unknown>;
	try {
		manifest = table(JSON.parse(text));
	} catch (error) {
		throw new Error(`could not parse ${file}: ${error}`);
	}

	return NODE_DEPENDENCIES.flatMap((field) =>
		Object.entries(table(manifest[field])).flatMap(([name, specifier]) => {
			if (typeof specifier !== "string") return [];
			const classified = classify(specifier);
			if (!classified) return [];
			return [
				{
					name,
					id: name,
					ecosystem: "node" as const,
					file,
					line: lineOf(text, name),
					specifier,
					raw: specifier,
					version: classified.version,
					precision: classified.precision,
					extras: [],
					marker: null,
					location: field,
				},
			];
		}),
	);
};
