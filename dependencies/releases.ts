/**
 * Turning a registry's version list into a catalogue.
 *
 * Each registry decides how its versions are read and ordered - PEP 440 for PyPI and for container
 * tags, semver for npm - and hands the result here, so the rules about what counts as the latest are
 * written once. A withdrawn release is kept in the list but never offered as somewhere to move to: `set`
 * still has to be able to validate a deliberate downgrade onto one.
 */

import type { Catalogue, Release } from "./types";

export const assemble = <T>(
	entries: T[],
	order: (a: T, b: T) => number,
	release: (entry: T) => Release,
	notes: string[] = [],
): Catalogue => {
	const releases = [...entries].sort(order).map(release);
	const usable = releases.filter(({ withdrawn }) => !withdrawn);
	const latestStable = usable.filter(({ prerelease }) => !prerelease).at(-1);
	const newest = usable.filter(({ prerelease }) => prerelease).at(-1);
	// a prerelease behind the newest release is not news: it is the one that release came out of
	const latestPrerelease =
		newest &&
		(!latestStable || releases.indexOf(newest) > releases.indexOf(latestStable))
			? newest
			: undefined;
	return { releases, latestStable, latestPrerelease, notes };
};

/** one note rather than one per version: a single unreadable release must not drown out the rest */
export const unreadableNote = (count: number, registry: string) =>
	count
		? [
				`${count} version${count === 1 ? "" : "s"} from ${registry} could not be read as a version`,
			]
		: [];
