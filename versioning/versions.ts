import path from "node:path";
import semver from "semver";
import { run } from "./git";
import { declaredVersion } from "./manifest";

export const RELEASE_TYPES = [
	"major",
	"premajor",
	"minor",
	"preminor",
	"patch",
	"prepatch",
	"prerelease",
	"release",
] as const;
export type ReleaseType = (typeof RELEASE_TYPES)[number];

export const PREIDS = ["alpha", "beta", "rc"] as const;
export type Preid = (typeof PREIDS)[number];

/** the types that leave the version in a prerelease, so need a stage to put it in */
const STAGED: ReleaseType[] = [
	"premajor",
	"preminor",
	"prepatch",
	"prerelease",
];

/** PEP 440 as uv normalises it: 0.4.0-alpha.1 and 0.4.0.a.1 are both stored as 0.4.0a1 */
const PEP440 = /^(\d+)\.(\d+)\.(\d+)(?:(a|b|rc)(\d+))?$/;
const STAGES = { a: "alpha", b: "beta", rc: "rc" } as const;

type Release = {
	major: number;
	minor: number;
	patch: number;
	prerelease: boolean;
	/** the prerelease stage, absent when there is none or it is not one we recognise */
	stage?: Preid;
	/** the version in semver form, so the two ecosystems can be compared the same way */
	semver: string;
};

const readPython = (version: string): Release => {
	const match = PEP440.exec(version);
	if (!match)
		throw new Error(
			`cannot bump ${version}: expected X.Y.Z, X.Y.ZaN, X.Y.ZbN or X.Y.ZrcN`,
		);
	const [, major, minor, patch, letter, counter] = match;
	const stage = letter ? STAGES[letter as keyof typeof STAGES] : undefined;
	const base = `${major}.${minor}.${patch}`;
	return {
		major: Number(major),
		minor: Number(minor),
		patch: Number(patch),
		prerelease: !!stage,
		stage,
		semver: stage ? `${base}-${stage}.${counter}` : base,
	};
};

const readNode = (version: string): Release => {
	const parsed = semver.parse(version);
	if (!parsed) throw new Error(`cannot bump ${version}: not valid semver`);
	return {
		major: parsed.major,
		minor: parsed.minor,
		patch: parsed.patch,
		prerelease: parsed.prerelease.length > 0,
		stage: PREIDS.find((preid) => preid === parsed.prerelease[0]),
		semver: version,
	};
};

const nextNode = (current: string, type: ReleaseType, stage?: Preid) => {
	// argument three is only read as the identifier when it is a string, so undefined means none
	const next = semver.inc(current, type, stage);
	if (!next) throw new Error(`cannot apply ${type} to ${current}`);
	return next;
};

/**
 * Which `uv version --bump` flags produce semver's answer. uv always advances where semver strips to the
 * base the version already has, so those cases go through `stable` instead, and a counter is only spelled
 * out when a prerelease is being created or switched to another stage.
 */
const bumps = (release: Release, type: ReleaseType, stage?: Preid) => {
	const strips =
		release.prerelease &&
		(type === "patch" ||
			(type === "minor" && release.patch === 0) ||
			(type === "major" && release.minor === 0 && release.patch === 0));
	switch (type) {
		case "release":
			return ["stable"];
		case "major":
		case "minor":
		case "patch":
			return strips ? ["stable"] : [type];
		case "premajor":
			return ["major", `${stage}=0`];
		case "preminor":
			return ["minor", `${stage}=0`];
		case "prepatch":
			return ["patch", `${stage}=0`];
		case "prerelease":
			if (!release.prerelease) return ["patch", `${stage}=0`];
			return release.stage === stage ? [`${stage}`] : [`${stage}=0`];
	}
};

const nextPython = async (
	dir: string,
	release: Release,
	type: ReleaseType,
	stage?: Preid,
) => {
	const args = bumps(release, type, stage).flatMap((bump) => ["--bump", bump]);
	// uv computes, we never let it write: it would lock, and the containers can only lock inside Docker
	const { stdout } = await run(
		["uv", "version", "--dry-run", "--short", ...args],
		{ cwd: dir },
	);
	return stdout.trim();
};

/**
 * The version a package would move to, worked out without touching it, so a whole release can be planned
 * and rejected before anything is written.
 *
 * `preid` is only used by the prerelease types: given none, an existing prerelease keeps its stage and a
 * stable version starts at alpha. Refuses `release` on a version that is already one, and refuses any bump
 * whose result would not be higher than the current version.
 */
export const nextVersion = async (
	repoDir: string,
	packageDir: string,
	type: ReleaseType,
	preid?: Preid,
) => {
	if (preid && !PREIDS.includes(preid))
		throw new Error(`unknown preid ${preid}, expected ${PREIDS.join(", ")}`);
	const { type: ecosystem, version: current } = await declaredVersion(
		repoDir,
		packageDir,
	);
	const release =
		ecosystem === "node" ? readNode(current) : readPython(current);
	if (type === "release" && !release.prerelease)
		throw new Error(`${current} is already a release`);

	const stage = STAGED.includes(type)
		? (preid ?? release.stage ?? "alpha")
		: undefined;
	const next =
		ecosystem === "node"
			? nextNode(current, type, stage)
			: await nextPython(path.join(repoDir, packageDir), release, type, stage);

	const compared = ecosystem === "node" ? next : readPython(next).semver;
	if (!semver.gt(compared, release.semver))
		throw new Error(
			`${type} would move ${current} to ${next}, which is not higher`,
		);
	return { current, next };
};
