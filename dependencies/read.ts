/**
 * Every third party pin in the working tree, grouped by dependency.
 *
 * Grouping is what delivers "the same version everywhere": a dependency is one row however many files
 * name it, and whether those files agree is a property of the row rather than something a reader has to
 * notice. Grouping is scoped to an ecosystem for the reason versioning/deps.ts already gives - the same
 * code ships twice under names that are otherwise easy to confuse - so a python httpx and a node one
 * would never be merged.
 *
 * Our own packages are excluded, and detected rather than listed: every manifest found here belongs to
 * one, so its declared name is an internal name. That stays correct when a package is added or renamed,
 * which a hardcoded list would not.
 */

import path from "node:path";
import { nameIn, normalise } from "../versioning/manifest";
import { composePins, dockerfilePins } from "./docker";
import { ecosystemOf, pinFiles } from "./files";
import { nodePins } from "./node";
import { pythonPins } from "./python";
import {
	type Agreement,
	type Dependency,
	type Kind,
	PRECISIONS,
	type Pin,
	type Precision,
} from "./types";

/** the images we publish ourselves, which versioning/bump.ts moves */
const OURS = /^infosecinnovations\//;

const MANIFESTS = new Set(["package.json", "pyproject.toml"]);

const pinsIn = (file: string, kind: Kind, text: string): Pin[] => {
	switch (kind) {
		case "node":
			return nodePins(file, text);
		case "python":
			return pythonPins(file, text);
		case "compose":
			return composePins(file, text);
		case "dockerfile":
			return dockerfilePins(file, text);
	}
};

/** the names our own manifests declare, keyed the way a pin's id is spelled */
const declaredNames = async (
	repoDir: string,
	files: { file: string; kind: Kind }[],
) => {
	const found = await Promise.all(
		files.map(async ({ file, kind }) => {
			if (!MANIFESTS.has(path.posix.basename(file))) return null;
			const name = nameIn(
				file,
				await Bun.file(path.join(repoDir, file)).text(),
			);
			if (!name) return null;
			return `${ecosystemOf(kind)}:${kind === "python" ? normalise(name) : name}`;
		}),
	);
	return new Set(found.filter((key): key is string => !!key));
};

const commonest = (values: string[]) => {
	const counts = new Map<string, number>();
	for (const value of values) counts.set(value, (counts.get(value) ?? 0) + 1);
	return [...counts].sort(
		(a, b) => b[1] - a[1] || (a[0] < b[0] ? -1 : 1),
	)[0]?.[0] as string;
};

const leastPrecise = (precisions: Precision[]) =>
	precisions.reduce((worst, precision) =>
		PRECISIONS.indexOf(precision) < PRECISIONS.indexOf(worst)
			? precision
			: worst,
	);

/** every occurrence of one dependency, and whether they agree with each other */
export const group = (pins: Pin[]): Dependency[] => {
	const byId = new Map<string, Pin[]>();
	for (const pin of pins) {
		const key = `${pin.ecosystem}:${pin.id}`;
		byId.set(key, [...(byId.get(key) ?? []), pin]);
	}

	return [...byId.values()]
		.map((occurrences): Dependency => {
			const first = occurrences[0] as Pin;
			const versions = [
				...new Set(
					occurrences.flatMap((pin) => (pin.version ? [pin.version] : [])),
				),
			].sort();
			const named = occurrences.filter((pin) => pin.version).length;
			const specifiers = new Set(occurrences.map((pin) => pin.specifier));
			const agreement: Agreement =
				// two ranges naming no version still disagree: commander is ^15.0.0 in the root and
				// ^14.0.2 in shabti_cli, which is a real divergence that no version number reveals
				versions.length > 1 || (!versions.length && specifiers.size > 1)
					? "diverged"
					: // some name a version and some do not: legitimate when a library floats what an app pins
						named > 0 && named < occurrences.length
						? "partial"
						: "agreed";
			return {
				id: first.id,
				ecosystem: first.ecosystem,
				name: commonest(occurrences.map((pin) => pin.name)),
				occurrences,
				versions,
				agreement,
				precision: leastPrecise(occurrences.map((pin) => pin.precision)),
				...(first.image
					? {
							image: {
								registry: first.image.registry,
								repository: first.image.repository,
							},
						}
					: {}),
			};
		})
		.sort(
			(a, b) =>
				a.ecosystem.localeCompare(b.ecosystem) || a.id.localeCompare(b.id),
		);
};

/** every third party pin in the working tree, ours excluded */
export const readPins = async (repoDir: string) => {
	const files = await pinFiles(repoDir);
	const ours = await declaredNames(repoDir, files);
	const pins = (
		await Promise.all(
			files.map(async ({ file, kind }) =>
				pinsIn(file, kind, await Bun.file(path.join(repoDir, file)).text()),
			),
		)
	).flat();
	return pins.filter(
		(pin) =>
			!ours.has(`${pin.ecosystem}:${pin.id}`) &&
			!(pin.ecosystem === "docker" && OURS.test(pin.id)),
	);
};

/** every third party dependency in the working tree, grouped and ordered */
export const readDependencies = async (repoDir: string) =>
	group(await readPins(repoDir));
