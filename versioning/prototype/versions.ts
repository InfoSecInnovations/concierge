import semver from "semver";

export type ReleaseType = "alpha" | "rc" | "latest";
export type Importance = "major" | "minor" | "patch";
export type SemverLevel = "major" | "minor" | "patch";

export const RELEASE_TYPES: ReleaseType[] = ["alpha", "rc", "latest"];
export const IMPORTANCES: Importance[] = ["major", "minor", "patch"];

// Until Shabti reaches 1.0 we use 0.x.y where x is the feature set and y is used for hotfixes, so
// the requested importance is shifted down a field. Once anything reaches 1.0 it maps straight
// through. See docs/developer/VERSIONING.md
const PRE_1_0_SHIFT = {
	major: "minor",
	minor: "patch",
	patch: "patch",
} as const satisfies Record<Importance, SemverLevel>;

const LEVEL_RANK = { patch: 0, minor: 1, major: 2 } as const;
const STAGE_RANK = { alpha: 0, beta: 1, rc: 2 } as const;

type Stage = keyof typeof STAGE_RANK;

export const effectiveLevel = (
	current: string,
	importance: Importance,
): SemverLevel =>
	semver.major(current) === 0 ? PRE_1_0_SHIFT[importance] : importance;

// which stage a prerelease belongs to, tolerating the non conforming tags in our release history
// (0.8.0-rc10, 0.7a3) as well as the ones we generate ourselves (0.9.0-alpha.1)
export const stageOf = (version: string): Stage | undefined => {
	const identifiers = semver.prerelease(version);
	if (!identifiers?.length) return undefined;
	const word = String(identifiers[0])
		.match(/^[a-z]+/i)?.[0]
		?.toLowerCase();
	if (!word) return undefined;
	if (word === "a" || word === "alpha") return "alpha";
	if (word === "b" || word === "beta") return "beta";
	if (word === "c" || word === "rc" || word === "pre" || word === "preview")
		return "rc";
	return undefined;
};

// the bump already in flight in a prerelease version, inferred from its trailing zeros: 0.9.0-alpha.1
// is a minor bump under way, 0.9.1-alpha.1 is a patch
const inFlightLevel = (version: string): SemverLevel =>
	semver.patch(version) !== 0
		? "patch"
		: semver.minor(version) !== 0
			? "minor"
			: "major";

const base = (version: string) =>
	`${semver.major(version)}.${semver.minor(version)}.${semver.patch(version)}`;

/**
 * The next version for a component, given the kind of release being made and whether the component
 * has changed since its baseline. An unchanged component keeps its version, the one exception being
 * a final release, which strips the prerelease suffix.
 */
export const computeVersion = (
	current: string,
	releaseType: ReleaseType,
	importance: Importance,
	changed: boolean,
): string => {
	if (!semver.valid(current))
		throw new Error(`not a valid semver version: ${current}`);
	const target = releaseType === "latest" ? undefined : releaseType;
	const level = effectiveLevel(current, importance);
	const isPrerelease = !!semver.prerelease(current)?.length;

	const next = (() => {
		if (!changed) return !target && isPrerelease ? base(current) : current;
		// a prerelease collapses to its base version, a stable version steps to the next one
		if (!target) return semver.inc(current, level);
		if (!isPrerelease) return semver.inc(current, `pre${level}`, target, "1");
		assertNoStageRegression(current, target);
		// escalate the base version if this release is more important than the bump already in
		// flight, otherwise carry on with the same base
		return LEVEL_RANK[level] > LEVEL_RANK[inFlightLevel(current)]
			? semver.inc(current, `pre${level}`, target, "1")
			: semver.inc(current, "prerelease", target, "1");
	})();

	if (!next)
		throw new Error(
			`could not derive the next version from ${current} (${releaseType}, ${importance})`,
		);
	assertMonotonic(current, next);
	return next;
};

// catches versions we cannot safely increment, e.g. semver reads the legacy 0.8.0-rc10 tag as a
// single string identifier, so the next rc it derives (0.8.0-rc.1) sorts *below* it
const assertMonotonic = (current: string, next: string) => {
	if (next !== current && !semver.gt(next, current))
		throw new Error(
			`refusing to move from ${current} to ${next}: the new version is not higher. ${current} is probably not a conforming prerelease, set it by hand before releasing.`,
		);
};

// alpha after rc would be a silent downgrade that PyPI and npm would both happily accept
const assertNoStageRegression = (current: string, target: Stage) => {
	const stage = stageOf(current);
	if (stage && STAGE_RANK[stage] > STAGE_RANK[target])
		throw new Error(
			`refusing to move from ${current} to a ${target} release: ${stage} is a later stage than ${target}.`,
		);
};

/**
 * PEP 440 normalised form of a semver version, which is what PyPI stores and what uv and hatchling
 * name their artifacts: 0.9.0-alpha.1 is published as 0.9.0a1. Both spellings are legal PEP 440 and
 * match each other in version specifiers, so the repository keeps the semver spelling everywhere and
 * only normalises when talking to PyPI.
 */
export const toPep440 = (version: string) => {
	const identifiers = semver.prerelease(version);
	if (!identifiers?.length) return base(version);
	const joined = identifiers.join("").toLowerCase();
	const match = joined.match(/^([a-z]+)(\d*)$/);
	if (!match)
		throw new Error(
			`cannot convert prerelease version ${version} to a PEP 440 version`,
		);
	const [, word, number] = match;
	const stage =
		word === "a" || word === "alpha"
			? "a"
			: word === "b" || word === "beta"
				? "b"
				: "rc";
	return `${base(version)}${stage}${number || "0"}`;
};

// npm dist-tag to publish under, so prereleases never take over "latest"
export const npmDistTag = (version: string) => stageOf(version) ?? "latest";
