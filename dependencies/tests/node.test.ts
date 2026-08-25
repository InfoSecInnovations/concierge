import { describe, expect, test } from "bun:test";
import { classify, nodePins } from "../node";
import type { Precision } from "../types";

describe("classify", () => {
	const cases: [string, Precision | null, string | null][] = [
		// the exact pins the repo already has
		["1.9.4", "exact", "1.9.4"],
		["26.6.4", "exact", "26.6.4"],
		["1.0.0-rc.1", "exact", "1.0.0-rc.1"],
		// the ranges it mostly has
		["^15.0.0", "range", null],
		["^14.0.2", "range", null],
		["~4.7.7", "range", null],
		["^5", "range", null],
		["5", "range", null],
		[">=1 <2", "range", null],
		["1.0.0 - 2.0.0", "range", null],
		["*", "range", null],
		["", "range", null],
		["x", "range", null],
		// a dist-tag is a real reference to whatever the registry points it at
		["latest", "tag", null],
		["next", "tag", null],
		["beta", "tag", null],
		// resolved by something other than a registry version, so there is nothing to be behind
		["workspace:*", null, null],
		["file:../shabti_api_client", null, null],
		["link:../x", null, null],
		["catalog:", null, null],
		["git+https://example.com/x.git", null, null],
		["github:user/repo", null, null],
		["https://example.com/x.tgz", null, null],
	];

	for (const [specifier, precision, version] of cases)
		test(`${JSON.stringify(specifier)} -> ${precision}`, () => {
			const classified = classify(specifier);
			if (precision === null) {
				expect(classified).toBeNull();
				return;
			}
			expect(classified?.precision).toBe(precision);
			expect(classified?.version).toBe(version);
		});

	const aliases: [string, string, string][] = [
		// the real one: an alias with no range at all, so every install resolves it afresh
		["npm:@jsr/std__ini", "@jsr/std__ini", ""],
		["npm:foo@^1", "foo", "^1"],
		["npm:@scope/pkg@^1.2.3", "@scope/pkg", "^1.2.3"],
		["npm:foo", "foo", ""],
	];

	for (const [specifier, target, range] of aliases)
		test(`${specifier} aliases ${target}`, () => {
			const classified = classify(specifier);
			expect(classified?.precision).toBe("alias");
			expect(classified?.version).toBeNull();
			expect(classified?.alias).toEqual({ target, range });
		});
});

/** the root package.json shape: tab indented, version last, a mix of exact pins, ranges and a tag */
const PACKAGE = `{
	"name": "shabti",
	"private": true,
	"devDependencies": {
		"@biomejs/biome": "1.9.4",
		"@types/bun": "latest",
		"@types/semver": "^7.7.1"
	},
	"peerDependencies": {
		"typescript": "^5"
	},
	"dependencies": {
		"commander": "^15.0.0",
		"semver": "^7.7.4",
		"@infosecinnovations/shabti-api-client": "workspace:*",
		"@std/ini": "npm:@jsr/std__ini"
	},
	"version": "0.8.0"
}
`;

describe("nodePins", () => {
	const pins = nodePins("package.json", PACKAGE);
	const byName = (name: string) => pins.find((pin) => pin.name === name);

	test("finds every dependency field and skips the workspace link", () => {
		expect(pins.map((pin) => pin.name).sort()).toEqual([
			"@biomejs/biome",
			"@std/ini",
			"@types/bun",
			"@types/semver",
			"commander",
			"semver",
			"typescript",
		]);
	});

	test("records which field each one came from", () => {
		expect(byName("commander")?.location).toBe("dependencies");
		expect(byName("@biomejs/biome")?.location).toBe("devDependencies");
		expect(byName("typescript")?.location).toBe("peerDependencies");
	});

	test("reads the precision of each shape", () => {
		expect(byName("@biomejs/biome")?.precision).toBe("exact");
		expect(byName("@biomejs/biome")?.version).toBe("1.9.4");
		expect(byName("commander")?.precision).toBe("range");
		expect(byName("@types/bun")?.precision).toBe("tag");
		expect(byName("@std/ini")?.precision).toBe("alias");
	});

	test("keeps npm names byte exact, unlike python's", () => {
		// PEP 503 folding would make these one dependency, and on npm they are two packages
		const pins = nodePins(
			"package.json",
			'{ "dependencies": { "foo-bar": "1.0.0", "foo_bar": "2.0.0" } }',
		);
		expect(pins.map((pin) => pin.id)).toEqual(["foo-bar", "foo_bar"]);
	});

	test("reports a name declared in two fields twice", () => {
		const pins = nodePins(
			"package.json",
			'{ "dependencies": { "x": "1.0.0" }, "peerDependencies": { "x": "^1" } }',
		);
		expect(pins.map((pin) => [pin.location, pin.specifier])).toEqual([
			["dependencies", "1.0.0"],
			["peerDependencies", "^1"],
		]);
	});

	test("recovers the line each one is written on", () => {
		expect(byName("@biomejs/biome")?.line).toBe(5);
		expect(byName("commander")?.line).toBe(13);
	});

	test("refuses a manifest it cannot parse", () => {
		expect(() => nodePins("package.json", "{ oops")).toThrow(
			/could not parse package\.json/,
		);
	});
});
