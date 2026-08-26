/**
 * The one table these commands print: a heading per section, an ecosystem under it, then name,
 * versions and where the pin lives. Nothing else. Why a row is in the report is the section it is in,
 * not a sentence trailing off the edge of the terminal, and the detail a table cannot hold is what
 * `--json` is for.
 */

import { ECOSYSTEMS, type Ecosystem } from "./types";

export type Row = { left: string; middle: string; right: string };

/** a row that still knows its ecosystem, which is what `byEcosystem` sorts it by */
export type Tagged = Row & { ecosystem: Ecosystem };

export type Group = { heading: string; entries: Row[] };

export type Section = { heading: string; groups: Group[] };

const pad = (text: string, width: number) => text.padEnd(width);

/** "1 file", "3 files" - the pluralised count every summary line ends up needing */
export const count = (n: number, thing: string) =>
	`${n} ${thing}${n === 1 ? "" : "s"}`;

/** where a dependency is pinned: the file itself when there is one, a count when there are several */
export const where = (files: string[]) => {
	const distinct = [...new Set(files)];
	return distinct.length === 1
		? (distinct[0] as string)
		: `${distinct.length} files`;
};

/**
 * One sub heading per ecosystem, in the order types.ts declares them, and always: a row whose
 * ecosystem is only implied by its filename is a row you have to work out.
 */
export const byEcosystem = (rows: Tagged[]): Group[] =>
	ECOSYSTEMS.map((ecosystem) => ({
		heading: ecosystem,
		entries: rows.filter((row) => row.ecosystem === ecosystem),
	}));

/**
 * Widths are measured across every row in every section rather than within each, so the whole output
 * is one table instead of several that happen to be stacked - which works because every row sits at
 * the same indent. An empty group prints nothing, and a section whose groups are all empty prints
 * nothing either, heading included.
 */
export const tabulate = (sections: Section[]) => {
	const all = sections.flatMap((section) =>
		section.groups.flatMap((group) => group.entries),
	);
	const left = Math.max(0, ...all.map((entry) => entry.left.length));
	const middle = Math.max(0, ...all.map((entry) => entry.middle.length));
	return sections.flatMap((section) => {
		const groups = section.groups.filter((group) => group.entries.length);
		return groups.length
			? [
					section.heading,
					...groups.flatMap((group) => [
						`  ${group.heading}`,
						...group.entries.map((entry) =>
							`    ${pad(entry.left, left)}  ${pad(entry.middle, middle)}  ${entry.right}`.trimEnd(),
						),
					]),
				]
			: [];
	});
};
