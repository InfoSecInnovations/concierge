import { describe, expect, test } from "bun:test";
import {
	type Importance,
	type ReleaseType,
	computeVersion,
	npmDistTag,
	toPep440,
} from "../versions";

const cases: [string, ReleaseType, Importance, boolean, string][] = [
	// pre 1.0, stable, changed: importance is shifted down a field
	["0.8.0", "alpha", "major", true, "0.9.0-alpha.1"],
	["0.8.0", "alpha", "minor", true, "0.8.1-alpha.1"],
	["0.8.0", "alpha", "patch", true, "0.8.1-alpha.1"],
	["0.8.0", "rc", "major", true, "0.9.0-rc.1"],
	["0.8.0", "latest", "major", true, "0.9.0"],
	["0.8.0", "latest", "minor", true, "0.8.1"],
	["0.8.0", "latest", "patch", true, "0.8.1"],
	// pre 1.0, prerelease, changed: the base is already the pending release
	["0.9.0-alpha.1", "alpha", "major", true, "0.9.0-alpha.2"],
	["0.9.0-alpha.1", "alpha", "patch", true, "0.9.0-alpha.2"],
	["0.9.0-alpha.1", "rc", "major", true, "0.9.0-rc.1"],
	["0.9.0-rc.1", "rc", "major", true, "0.9.0-rc.2"],
	["0.9.0-rc.1", "latest", "major", true, "0.9.0"],
	["0.9.0-alpha.3", "latest", "patch", true, "0.9.0"],
	// unless the release is more important than the bump already in flight
	["0.8.1-alpha.1", "alpha", "major", true, "0.9.0-alpha.1"],
	["0.8.1-alpha.1", "alpha", "minor", true, "0.8.1-alpha.2"],
	["0.8.1-alpha.1", "latest", "major", true, "0.9.0"],
	// unchanged components only move when a prerelease is promoted to a final release
	["0.3.0", "alpha", "major", false, "0.3.0"],
	["0.3.0", "rc", "major", false, "0.3.0"],
	["0.3.0", "latest", "major", false, "0.3.0"],
	["0.3.1-alpha.2", "alpha", "major", false, "0.3.1-alpha.2"],
	["0.3.1-alpha.2", "rc", "major", false, "0.3.1-alpha.2"],
	["0.3.1-alpha.2", "latest", "major", false, "0.3.1"],
	// once something reaches 1.0 the importance maps straight through
	["1.2.3", "latest", "major", true, "2.0.0"],
	["1.2.3", "latest", "minor", true, "1.3.0"],
	["1.2.3", "latest", "patch", true, "1.2.4"],
	["1.2.3", "alpha", "minor", true, "1.3.0-alpha.1"],
];

describe("computeVersion", () => {
	for (const [current, releaseType, importance, changed, expected] of cases) {
		test(`${current} + ${releaseType}/${importance}${changed ? "" : " unchanged"} -> ${expected}`, () => {
			expect(computeVersion(current, releaseType, importance, changed)).toBe(
				expected,
			);
		});
	}

	test("refuses to go back from a release candidate to an alpha", () => {
		expect(() => computeVersion("0.9.0-rc.4", "alpha", "major", true)).toThrow(
			/later stage/,
		);
	});

	test("refuses to increment a non conforming prerelease it cannot beat", () => {
		// semver reads rc10 as a single string identifier, so the rc it derives sorts below it
		expect(() => computeVersion("0.8.0-rc10", "rc", "major", true)).toThrow(
			/not higher/,
		);
	});

	test("rejects versions that are not semver", () => {
		expect(() => computeVersion("0.7a3", "alpha", "major", true)).toThrow(
			/not a valid semver/,
		);
	});
});

describe("toPep440", () => {
	for (const [version, expected] of [
		["0.9.0", "0.9.0"],
		["0.9.0-alpha.1", "0.9.0a1"],
		["0.9.0-beta.0", "0.9.0b0"],
		["0.9.0-rc.2", "0.9.0rc2"],
		["0.8.0-rc10", "0.8.0rc10"],
		["0.3.0-alpha", "0.3.0a0"],
	]) {
		test(`${version} -> ${expected}`, () => {
			expect(toPep440(version)).toBe(expected);
		});
	}
});

describe("npmDistTag", () => {
	test("keeps prereleases off the latest tag", () => {
		expect(npmDistTag("0.9.0")).toBe("latest");
		expect(npmDistTag("0.9.0-alpha.1")).toBe("alpha");
		expect(npmDistTag("0.9.0-rc.1")).toBe("rc");
	});
});
