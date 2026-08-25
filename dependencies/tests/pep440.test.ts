import { describe, expect, test } from "bun:test";
import { canonical, compare, highest, parse } from "../pep440";

/**
 * PEP 440's own "Summary of permitted suffixes and relative ordering" example, in order, extended with
 * an epoch and a second release at the end. Asserted as a whole rather than pair by pair, so every
 * adjacent pair is covered and a sort of any permutation has to reproduce all of it.
 */
const ASCENDING = [
	"1.dev0",
	"1.0.dev456",
	"1.0a1",
	"1.0a2.dev456",
	"1.0a12.dev456",
	"1.0a12",
	"1.0b1.dev456",
	"1.0b2",
	"1.0b2.post345.dev456",
	"1.0b2.post345",
	"1.0rc1.dev456",
	"1.0rc1",
	"1.0",
	"1.0+abc.5",
	"1.0+abc.7",
	"1.0+5",
	"1.0.post456.dev34",
	"1.0.post456",
	"1.0.1",
	"1.1.dev1",
	"1.1a1",
	"1.1",
	"2.0",
	"2!1.0",
];

const version = (text: string) => {
	const parsed = parse(text);
	if (!parsed) throw new Error(`${text} should parse`);
	return parsed;
};

const sorted = (versions: string[]) =>
	[...versions]
		.map(version)
		.sort(compare)
		.map((parsed) => parsed.canonical);

describe("ordering", () => {
	for (const [index, lower] of ASCENDING.slice(0, -1).entries()) {
		const higher = ASCENDING[index + 1] as string;
		test(`${lower} < ${higher}`, () => {
			expect(compare(version(lower), version(higher))).toBeLessThan(0);
			expect(compare(version(higher), version(lower))).toBeGreaterThan(0);
		});
	}

	test("sorting any permutation reproduces the whole order", () => {
		const expected = ASCENDING.map((text) => version(text).canonical);
		expect(sorted([...ASCENDING].reverse())).toEqual(expected);
		// a fixed interleave rather than a shuffle, so a failure is always reproducible
		const halves = ASCENDING.slice(0, 12).flatMap((text, index) => [
			text,
			ASCENDING[index + 12] as string,
		]);
		expect(sorted(halves)).toEqual(expected);
	});

	test("every version equals itself", () => {
		for (const text of ASCENDING)
			expect(compare(version(text), version(text))).toBe(0);
	});
});

describe("equality", () => {
	const same: string[][] = [
		// trailing zeros are not significant, so these are all one version
		["1", "1.0", "1.0.0", "1.0.0.0", "v1.0", " 1.0 "],
		// the case apache/tika forces: a four segment version against a two segment one
		["3.3", "3.3.0.0"],
		// an absent counter is an implicit zero
		["1.2a", "1.2a0", "1.2.a.0", "1.2-alpha-0"],
		["1.0.post", "1.0.post0", "1.0-r", "1.0.rev0"],
		["1.0dev", "1.0.dev0", "1.0-dev-0"],
		// zero padding is stripped everywhere, epoch included
		["01!1.0", "1!1.0", "1!1.0.0"],
		["1.0.01", "1.0.1"],
	];

	for (const group of same)
		test(group.join(" == "), () => {
			for (const other of group.slice(1))
				expect(compare(version(group[0] as string), version(other))).toBe(0);
		});

	test("an epoch is not free", () => {
		expect(compare(version("1!1.0"), version("1.0"))).toBeGreaterThan(0);
		// the epoch outranks everything, so a low version in a high epoch still wins
		expect(compare(version("1!1.0"), version("99.99.99"))).toBeGreaterThan(0);
	});
});

describe("normalisation", () => {
	const cases: [string, string][] = [
		["1.0", "1.0"],
		// release segments are printed as parsed: rewriting postgres 18.0 as 18 would be wrong
		["1.0.0", "1.0.0"],
		["3.3.0.0", "3.3.0.0"],
		["v1.0", "1.0"],
		[" 1.0 ", "1.0"],
		["0!1.0", "1.0"],
		["01!1.0", "1!1.0"],
		["1.0.01", "1.0.1"],
		// every spelling of a pre-release stage folds to a, b or rc
		["1.0a01", "1.0a1"],
		["1.0ALPHA2", "1.0a2"],
		["1.0-alpha-2", "1.0a2"],
		["1.0.beta1", "1.0b1"],
		["1.0_B2", "1.0b2"],
		["1.0c1", "1.0rc1"],
		["1.0pre1", "1.0rc1"],
		["1.0preview1", "1.0rc1"],
		["1.0RC1", "1.0rc1"],
		["1.0-rc1", "1.0rc1"],
		["1.2a", "1.2a0"],
		// post releases, including the bare dash form a Debian revision uses
		["1.0.post", "1.0.post0"],
		["1.0-1", "1.0.post1"],
		["1.0.rev3", "1.0.post3"],
		["1.0r3", "1.0.post3"],
		["1.0_dev", "1.0.dev0"],
		["1.0.dev456", "1.0.dev456"],
		["1.0+FOO_bar-1", "1.0+foo.bar.1"],
		["1.0b2.post345.dev456", "1.0b2.post345.dev456"],
	];

	for (const [input, expected] of cases)
		test(`${input} -> ${expected}`, () => {
			expect(canonical(input)).toBe(expected);
		});
});

describe("prerelease classification", () => {
	const prereleases = ["1.0a1", "1.0b2", "1.0rc1", "1.0.dev0", "1.0b2.post345"];
	const releases = ["1.0", "1.0.post1", "1.0+local", "3.3.0.0", "1!1.0"];

	for (const text of prereleases)
		test(`${text} is a prerelease`, () => {
			expect(version(text).prerelease).toBe(true);
		});

	for (const text of releases)
		test(`${text} is not a prerelease`, () => {
			expect(version(text).prerelease).toBe(false);
		});
});

describe("rejections", () => {
	// docker tags are the reason this list matters: the same regex filters candidate tags, so
	// anything here is a tag that must not be mistaken for a version
	const rejected = [
		"",
		" ",
		"latest",
		"nightly",
		"trixie",
		"stable",
		"18-alpine",
		"18.3-alpine3.22",
		"18-bookworm",
		"4.0.0-SNAPSHOT",
		"server-cuda-b9843",
		"b9843",
		"sha-0649641",
		"1.0.0.",
		".1",
		"1..0",
		"1.0-",
		"1.0+",
		"1.0+_bad",
		"${VERSION}",
		"python3.14-trixie-slim",
	];

	for (const text of rejected)
		test(`${JSON.stringify(text)} is not a version`, () => {
			expect(parse(text)).toBeNull();
			expect(canonical(text)).toBeNull();
		});
});

describe("versions this repo actually pins", () => {
	// every third party pin in the repo today, plus the upstream shapes they will move to
	const unchanged = [
		"0.136.3",
		"1.6.3",
		"3.0.0",
		"5.8.1",
		"3.1.0",
		"0.30.1",
		"4.3.0",
		"0.12.11",
		"4.14.3",
		"1.2.0",
		"4.15.0",
		"0.11.1",
		"18.3",
		"26.5.6",
		"26.6.4",
		"3.5.0",
		"3.3.0.0",
		"1.9.4",
		"0.1",
	];

	for (const text of unchanged)
		test(`${text} parses unchanged`, () => {
			expect(canonical(text)).toBe(text);
		});

	// the odd shapes the real registries return, all seen live
	const upstream: [string, string][] = [
		["3.0.0-beta1", "3.0.0b1"],
		["4.0.0-1", "4.0.0.post1"],
		["4.0.0-alpha-1", "4.0.0a1"],
		["4.0.0-beta-1", "4.0.0b1"],
		["10-rc1", "10rc1"],
	];

	for (const [input, expected] of upstream)
		test(`${input} -> ${expected}`, () => {
			expect(canonical(input)).toBe(expected);
		});
});

describe("highest", () => {
	test("finds the highest of a real tag list", () => {
		expect(
			highest(["18.3", "19.0", "18.4", "17.9"].map(version))?.canonical,
		).toBe("19.0");
	});

	test("prefers the more precise of two equal versions", () => {
		// the whole point: postgres publishes a floating `19` alongside the concrete `19.0`, and
		// PEP 440 calls them equal, so without the tie-break the floating tag could win
		expect(highest(["19", "19.0"].map(version))?.canonical).toBe("19.0");
		expect(highest(["19.0", "19"].map(version))?.canonical).toBe("19.0");
		expect(highest(["3.3", "3.3.0.0"].map(version))?.canonical).toBe("3.3.0.0");
	});

	test("prefers a release over its prereleases", () => {
		expect(highest(["1.0rc1", "1.0", "1.0a1"].map(version))?.canonical).toBe(
			"1.0",
		);
	});

	test("has no answer for nothing", () => {
		expect(highest([])).toBeUndefined();
	});
});

describe("ordering is a total order over a real version list", () => {
	/**
	 * Every version ruff has published, as PyPI lists them. There is no committed expected order here
	 * on purpose: hand-authoring one would only assert that this module agrees with whatever I believed
	 * when I wrote it. Asserting the properties a correct comparator must have is the honest check, and
	 * the authoritative ordering lives in the spec example above.
	 */
	const REAL = [
		"0.0.1",
		"0.0.2",
		"0.0.3",
		"0.0.10",
		"0.0.100",
		"0.0.200",
		"0.0.247",
		"0.1.0",
		"0.1.9",
		"0.1.15",
		"0.2.0",
		"0.2.2",
		"0.3.0",
		"0.3.7",
		"0.4.0",
		"0.4.10",
		"0.5.0",
		"0.5.7",
		"0.6.0",
		"0.6.9",
		"0.7.0",
		"0.7.4",
		"0.8.0",
		"0.8.6",
		"0.9.0",
		"0.9.10",
		"0.10.0",
		"0.11.0",
		"0.11.13",
		"0.12.0",
		"0.12.11",
		"0.13.0",
		"0.14.0",
		"0.15.0",
		"0.15.4",
	];

	const parsed = REAL.map(version);

	test("every version parses", () => {
		expect(parsed).toHaveLength(REAL.length);
	});

	test("is antisymmetric", () => {
		// asserted as a sum rather than as one sign against the other's negation: the pairs include
		// every version against itself, where both signs are zero and one of them would be negative zero
		for (const a of parsed)
			for (const b of parsed)
				expect(Math.sign(compare(a, b)) + Math.sign(compare(b, a))).toBe(0);
	});

	test("is transitive", () => {
		const ordered = [...parsed].sort(compare);
		for (const [index, lower] of ordered.slice(0, -1).entries())
			expect(
				compare(lower, ordered[index + 1] as (typeof ordered)[number]),
			).toBeLessThan(0);
	});

	test("orders by release segment, not by string", () => {
		// the failure a naive string compare gives: "0.0.100" below "0.0.2", "0.10.0" below "0.9.0"
		expect(compare(version("0.0.2"), version("0.0.100"))).toBeLessThan(0);
		expect(compare(version("0.9.0"), version("0.10.0"))).toBeLessThan(0);
		expect(compare(version("0.2.0"), version("0.11.0"))).toBeLessThan(0);
	});
});
