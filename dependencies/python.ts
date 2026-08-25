/**
 * Reading the python pins out of a pyproject.toml or a requirements file.
 *
 * The TOML is parsed rather than scanned, so a requirement is found wherever it is declared and a
 * malformed file is a failure rather than an empty answer. The requirement string inside it is then
 * matched against the shapes this repo actually writes rather than the whole PEP 508 grammar - what is
 * needed is enough structure to put the pieces back when a pin is rewritten.
 */

import path from "node:path";
import { normalise, requirementsIn } from "../versioning/manifest";
import type { Pin, Precision } from "./types";

export type Requirement = {
	name: string;
	extras: string[];
	/** everything between the extras and the marker, as written */
	specifier: string;
	/** a PEP 508 environment marker, kept verbatim so a rewrite can put it back */
	marker: string | null;
};

const REQUIREMENT =
	/^\s*([A-Za-z0-9][A-Za-z0-9._-]*)\s*(?:\[([^\]]*)\])?\s*([^;]*?)\s*(?:;\s*(.*?))?\s*$/;

/**
 * One requirement split into the parts a rewrite has to put back, or null when it is a shape this tool
 * does not manage. Today that means only a PEP 508 direct reference, `foo @ https://...`, whose version
 * is decided by a URL rather than by a registry.
 */
export const parseRequirement = (requirement: string): Requirement | null => {
	const match = REQUIREMENT.exec(requirement);
	if (!match) return null;
	const [, name, extras, specifier, marker] = match;
	if ((specifier as string).startsWith("@")) return null;
	return {
		name: name as string,
		extras: extras
			? extras
					.split(",")
					.map((extra) => extra.trim())
					.filter((extra) => !!extra)
			: [],
		specifier: specifier as string,
		marker: marker ?? null,
	};
};

const CLAUSE = /^(===|==|~=|!=|<=|>=|<|>)\s*(.+)$/;

/** how tightly a specifier set constrains the version, and the version it names when it names one */
export const precisionOf = (
	specifier: string,
): { precision: Precision; version: string | null } => {
	const trimmed = specifier.trim();
	if (!trimmed) return { precision: "absent", version: null };
	// a multi clause set never names one version, so there is nothing to report and nothing to guess
	if (trimmed.includes(",")) return { precision: "range", version: null };
	const match = CLAUSE.exec(trimmed);
	if (!match) return { precision: "range", version: null };
	const [, operator, value] = match;
	const version = (value as string).trim();
	switch (operator) {
		case "===":
			return { precision: "exact", version };
		case "==":
			// `==1.*` is a range wearing an equals sign
			return version.includes("*")
				? { precision: "range", version: null }
				: { precision: "exact", version };
		case "~=":
			return { precision: "compatible", version };
		default:
			return { precision: "range", version: null };
	}
};

/**
 * The line a requirement is written on. Parsing the TOML loses it, so it is recovered by searching the
 * raw text, and a miss reports 0 rather than failing: the line is only ever shown to a human.
 */
const lineOf = (text: string, requirement: string) => {
	const at = text.indexOf(requirement);
	return at < 0 ? 0 : text.slice(0, at).split("\n").length;
};

/** a requirements file, which has no tables: one requirement per line, minus comments and options */
const requirementLines = (text: string) =>
	text.split("\n").flatMap((line, index) => {
		const stripped = line.replace(/(^|\s)#.*$/, "").trim();
		// `-r other.txt`, `-e .`, `--index-url ...`: options rather than requirements
		if (!stripped || stripped.startsWith("-")) return [];
		return [
			{ requirement: stripped, location: "requirements", line: index + 1 },
		];
	});

/** every third party pin a python manifest declares */
export const pythonPins = (file: string, text: string): Pin[] => {
	const declared =
		path.posix.basename(file) === "pyproject.toml"
			? requirementsIn(file, text).map((entry) => ({
					...entry,
					line: lineOf(text, entry.requirement),
				}))
			: requirementLines(text);

	return declared.flatMap(({ requirement, location, line }) => {
		const parsed = parseRequirement(requirement);
		if (!parsed) return [];
		const { precision, version } = precisionOf(parsed.specifier);
		return [
			{
				name: parsed.name,
				id: normalise(parsed.name),
				ecosystem: "python" as const,
				file,
				line,
				specifier: parsed.specifier,
				raw: requirement,
				version,
				precision,
				extras: parsed.extras,
				marker: parsed.marker,
				location,
			},
		];
	});
};
