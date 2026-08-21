import { describe, expect, test } from "bun:test";
import {
	type Preid,
	type ReleaseType,
	nextVersion,
	npmDistTag,
} from "../versions";
import { nodePackage, pythonPackage, useRepo } from "./fixture";

type Case = [string, ReleaseType, Preid | undefined, string];

const NODE: Case[] = [
	["0.3.0", "major", undefined, "1.0.0"],
	["0.3.0", "minor", undefined, "0.4.0"],
	["0.3.0", "patch", undefined, "0.3.1"],
	["0.3.0", "premajor", "alpha", "1.0.0-alpha.0"],
	["0.3.0", "preminor", "alpha", "0.4.0-alpha.0"],
	["0.3.0", "prepatch", "alpha", "0.3.1-alpha.0"],
	["0.3.0", "preminor", "rc", "0.4.0-rc.0"],
	// no preid on a stable version starts at alpha, rather than semver's bare 0.3.1-0
	["0.3.0", "prerelease", undefined, "0.3.1-alpha.0"],
	// a non prerelease type strips to the base it already has, or advances past it
	["0.4.0-alpha.0", "major", undefined, "1.0.0"],
	["0.4.0-alpha.0", "minor", undefined, "0.4.0"],
	["0.4.0-alpha.0", "patch", undefined, "0.4.0"],
	["0.4.0-alpha.0", "release", undefined, "0.4.0"],
	// no preid on a prerelease keeps its stage
	["0.4.0-alpha.0", "prerelease", undefined, "0.4.0-alpha.1"],
	["0.4.0-alpha.0", "prerelease", "alpha", "0.4.0-alpha.1"],
	// switching stage restarts the counter
	["0.4.0-alpha.0", "prerelease", "rc", "0.4.0-rc.0"],
	["0.4.0-alpha.0", "preminor", undefined, "0.5.0-alpha.0"],
	["0.4.0-alpha.0", "prepatch", undefined, "0.4.1-alpha.0"],
	["0.4.1-alpha.0", "major", undefined, "1.0.0"],
	["0.4.1-alpha.0", "minor", undefined, "0.5.0"],
	["0.4.1-alpha.0", "patch", undefined, "0.4.1"],
	["0.4.0-rc.0", "prerelease", undefined, "0.4.0-rc.1"],
	["0.4.0-rc.0", "minor", undefined, "0.4.0"],
	["1.0.0-alpha.0", "major", undefined, "1.0.0"],
];

const PYTHON: Case[] = [
	["0.3.0", "major", undefined, "1.0.0"],
	["0.3.0", "minor", undefined, "0.4.0"],
	["0.3.0", "patch", undefined, "0.3.1"],
	["0.3.0", "premajor", "alpha", "1.0.0a0"],
	["0.3.0", "preminor", "alpha", "0.4.0a0"],
	["0.3.0", "prepatch", "alpha", "0.3.1a0"],
	["0.3.0", "preminor", "rc", "0.4.0rc0"],
	["0.3.0", "prerelease", undefined, "0.3.1a0"],
	["0.4.0a0", "major", undefined, "1.0.0"],
	["0.4.0a0", "minor", undefined, "0.4.0"],
	["0.4.0a0", "patch", undefined, "0.4.0"],
	["0.4.0a0", "release", undefined, "0.4.0"],
	["0.4.0a0", "prerelease", undefined, "0.4.0a1"],
	["0.4.0a0", "prerelease", "alpha", "0.4.0a1"],
	["0.4.0a0", "prerelease", "rc", "0.4.0rc0"],
	["0.4.0a0", "preminor", undefined, "0.5.0a0"],
	["0.4.0a0", "prepatch", undefined, "0.4.1a0"],
	["0.4.1a0", "major", undefined, "1.0.0"],
	["0.4.1a0", "minor", undefined, "0.5.0"],
	["0.4.1a0", "patch", undefined, "0.4.1"],
	["0.4.0rc0", "prerelease", undefined, "0.4.0rc1"],
	["0.4.0rc0", "minor", undefined, "0.4.0"],
	["1.0.0a0", "major", undefined, "1.0.0"],
];

const starts = (cases: Case[]) => [
	...new Set(cases.map(([current]) => current)),
];

const nodeName = (version: string) => `node-${version.replace(/[.-]/g, "-")}`;
const pythonName = (version: string) =>
	`python-${version.replaceAll(".", "-")}`;
const pythonDir = (version: string) => pythonName(version).replaceAll("-", "_");

const label = ([current, type, preid, next]: Case) =>
	`${current} + ${type}${preid ? ` --preid ${preid}` : ""} -> ${next}`;

describe("node versions", () => {
	const repo = useRepo({
		packages: starts(NODE).map((version) =>
			nodePackage(nodeName(version), version),
		),
	});

	for (const testCase of NODE) {
		const [current, type, preid, next] = testCase;
		test(label(testCase), async () => {
			expect(
				await nextVersion(repo.dir, nodeName(current), type, preid),
			).toEqual({ current, next });
		});
	}
});

describe("python versions", () => {
	const repo = useRepo({
		packages: starts(PYTHON).map((version) =>
			pythonPackage(pythonName(version), version),
		),
	});

	for (const testCase of PYTHON) {
		const [current, type, preid, next] = testCase;
		test(label(testCase), async () => {
			expect(
				await nextVersion(repo.dir, pythonDir(current), type, preid),
			).toEqual({ current, next });
		});
	}
});

describe("npmDistTag", () => {
	test("keeps prereleases off the latest tag", () => {
		expect(npmDistTag("0.9.0")).toBe("latest");
		expect(npmDistTag("0.9.0-alpha.1")).toBe("alpha");
		expect(npmDistTag("0.9.0-rc.1")).toBe("rc");
		expect(npmDistTag("0.8.0-rc10")).toBe("rc10");
	});
});

describe("refusals", () => {
	const repo = useRepo({
		packages: [
			nodePackage("node-stable", "0.3.0"),
			nodePackage("node-rc", "0.4.0-rc.0"),
			nodePackage("node-odd", "0.4.0-rc10"),
			pythonPackage("python-stable", "0.3.0"),
			pythonPackage("python-rc", "0.4.0rc0"),
			pythonPackage("python-post", "0.4.0.post1"),
			pythonPackage("python-unversioned", "0.1.0", {
				files: { "pyproject.toml": '[project]\nname = "python-unversioned"\n' },
			}),
		],
	});

	test("refuses release on a version that is already one", async () => {
		await expect(
			nextVersion(repo.dir, "node-stable", "release"),
		).rejects.toThrow(/already a release/);
		await expect(
			nextVersion(repo.dir, "python_stable", "release"),
		).rejects.toThrow(/already a release/);
	});

	test("refuses a stage that would move the version backwards", async () => {
		await expect(
			nextVersion(repo.dir, "node-rc", "prerelease", "alpha"),
		).rejects.toThrow(/not higher/);
		// uv is the one refusing on the python side
		await expect(
			nextVersion(repo.dir, "python_rc", "prerelease", "alpha"),
		).rejects.toThrow();
	});

	test("refuses a prerelease tag it cannot beat", async () => {
		// semver reads rc10 as one string identifier, which the rc.0 it derives sorts below
		await expect(
			nextVersion(repo.dir, "node-odd", "prerelease", "rc"),
		).rejects.toThrow(/not higher/);
	});

	test("refuses an unknown preid", async () => {
		await expect(
			nextVersion(repo.dir, "node-stable", "preminor", "gamma" as Preid),
		).rejects.toThrow(/unknown preid/);
	});

	test("refuses a python version it cannot read", async () => {
		await expect(nextVersion(repo.dir, "python_post", "patch")).rejects.toThrow(
			/cannot bump 0\.4\.0\.post1/,
		);
	});

	test("refuses a manifest with no version", async () => {
		await expect(
			nextVersion(repo.dir, "python_unversioned", "patch"),
		).rejects.toThrow(/no version declared/);
	});
});
