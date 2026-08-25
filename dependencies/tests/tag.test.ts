import { describe, expect, test } from "bun:test";
import { type TagShape, matching, newest, shapeOf } from "../tag";

describe("shapeOf", () => {
	const cases: [string, TagShape | null][] = [
		// every image pin in the repo today
		["18.3", { prefix: "", label: "", slot: "version", value: "18.3" }],
		["3.5.0", { prefix: "", label: "", slot: "version", value: "3.5.0" }],
		["26.5.6", { prefix: "", label: "", slot: "version", value: "26.5.6" }],
		[
			"3.3.0.0-full",
			{ prefix: "", label: "-full", slot: "version", value: "3.3.0.0" },
		],
		[
			"0.11.1-python3.14-trixie-slim",
			{
				prefix: "",
				label: "-python3.14-trixie-slim",
				slot: "version",
				value: "0.11.1",
			},
		],
		[
			"server-cuda-b9843",
			{ prefix: "server-cuda-", label: "", slot: "build", value: "b9843" },
		],
		// a whole-tag version wins over the segment scan, so a prerelease is not read as a label
		["10-rc1", { prefix: "", label: "", slot: "version", value: "10-rc1" }],
		[
			"4.0.0-alpha-1",
			{ prefix: "", label: "", slot: "version", value: "4.0.0-alpha-1" },
		],
		["v1.2.3", { prefix: "", label: "", slot: "version", value: "v1.2.3" }],
		// no version and no build counter: nothing to compare against
		["latest", null],
		["nightly", null],
		["main", null],
		["trixie", null],
		["python3.14-trixie-slim", null],
		["server-cuda-latest", null],
	];

	for (const [tag, expected] of cases)
		test(`${tag} -> ${expected ? JSON.stringify(expected) : "null"}`, () => {
			expect(shapeOf(tag)).toEqual(expected);
		});
});

describe("matching", () => {
	const TAGS = [
		"latest",
		"latest-full",
		"0.11.1",
		"0.11.1-python3.14-trixie-slim",
		"sha-0649641-python3.14-trixie-slim",
		"python3.14-trixie-slim",
		"18-alpine",
		"18.3-alpine3.22",
		"18-bookworm",
		"3.3.0.0-full",
		"4.0.0-SNAPSHOT-full",
	];

	test("anchors on the label and rejects the decoys", () => {
		expect(
			matching(TAGS, "", "-python3.14-trixie-slim", "version").map(
				({ tag }) => tag,
			),
		).toEqual(["0.11.1-python3.14-trixie-slim"]);
	});

	test("rejects every tag that is not a version", () => {
		// -alpine and -bookworm are a different label, and latest is not a version at all
		expect(matching(TAGS, "", "", "version").map(({ tag }) => tag)).toEqual([
			"0.11.1",
		]);
	});

	test("reads a snapshot as a dev release", () => {
		const found = matching(TAGS, "", "-full", "version");
		// ascending, and latest-full is rejected because `latest` is not a version
		expect(found.map(({ tag }) => tag)).toEqual([
			"3.3.0.0-full",
			"4.0.0-SNAPSHOT-full",
		]);
		const snapshot = found[1];
		expect(snapshot?.version?.canonical).toBe("4.0.0.dev0");
		// unreleased, so it must never be offered as somewhere to move a pin to
		expect(snapshot?.version?.prerelease).toBe(true);
	});

	test("reads a build counter as a number, not a string", () => {
		const tags = [
			"server-cuda-b9843",
			"server-cuda-b10412",
			"server-cuda-b9999",
		];
		expect(
			matching(tags, "server-cuda-", "", "build").map(({ build }) => build),
		).toEqual([9843, 9999, 10412]);
	});
});

describe("newest", () => {
	test("finds the real major through the version stream", () => {
		// apache/tika, pinned at 3.3.0.0-full. Comparing labelled tags alone makes 3.3.1.0-full look
		// like the answer, because 4.0.0-full has three release segments where the pin has four. Asking
		// the unlabelled stream first gives 4.0.0, and 4.0.0-full exists.
		const tags = [
			"latest",
			"latest-full",
			"3.3.0.0",
			"3.3.0.0-full",
			"3.3.1.0",
			"3.3.1.0-full",
			"4.0.0",
			"4.0.0-full",
			"4.0.0-SNAPSHOT",
			"4.0.0-SNAPSHOT-full",
		];
		const selection = newest(shapeOf("3.3.0.0-full") as TagShape, tags);
		expect(selection.latest?.tag).toBe("4.0.0-full");
		expect(selection.stream?.tag).toBe("4.0.0");
		expect(selection.how).toBe("stream");
		// the dev build is ahead of 4.0.0 only in the sense of being unreleased, so it is not offered
		expect(selection.prerelease).toBeUndefined();
	});

	test("falls back to the highest labelled tag when the stream has no counterpart", () => {
		// astral/uv: 0.13.0 exists but was never published for this base image
		const tags = [
			"latest",
			"0.11.1",
			"0.12.0",
			"0.12.3",
			"0.13.0",
			"0.11.1-python3.14-trixie-slim",
			"0.12.0-python3.14-trixie-slim",
			"0.12.3-python3.14-trixie-slim",
			"0.12.3-python3.13-trixie-slim",
			"0.13.0-python3.15-forky-slim",
			"sha-0649641-python3.14-trixie-slim",
			"python3.14-trixie-slim",
		];
		const selection = newest(
			shapeOf("0.11.1-python3.14-trixie-slim") as TagShape,
			tags,
		);
		expect(selection.latest?.tag).toBe("0.12.3-python3.14-trixie-slim");
		expect(selection.stream?.tag).toBe("0.13.0");
		expect(selection.how).toBe("label");
		// a newer uv for a different Python or a different Debian base is out of view by design
		expect(selection.all.map(({ tag }) => tag)).not.toContain(
			"0.13.0-python3.15-forky-slim",
		);
	});

	test("never recommends a floating tag over the concrete release it aliases", () => {
		// postgres publishes 19 alongside 19.0 and 19.1, and PEP 440 calls 19 and 19.0 equal
		const tags = [
			"latest",
			"17.9",
			"18",
			"18.3",
			"18.4",
			"19",
			"19.0",
			"19.1",
			"18-alpine",
			"18.3-alpine3.22",
			"18-bookworm",
			"trixie",
		];
		const selection = newest(shapeOf("18.3") as TagShape, tags);
		expect(selection.latest?.tag).toBe("19.1");
		expect(selection.how).toBe("stream");
	});

	test("prefers the more precise of two equal tags", () => {
		const selection = newest(shapeOf("18.3") as TagShape, [
			"18.3",
			"19",
			"19.0",
		]);
		expect(selection.latest?.tag).toBe("19.0");
	});

	test("reports a prerelease only when it is ahead of the newest release", () => {
		const behind = newest(shapeOf("18.3") as TagShape, [
			"18.3",
			"19.1",
			"10-rc1",
		]);
		expect(behind.prerelease).toBeUndefined();
		const ahead = newest(shapeOf("18.3") as TagShape, [
			"18.3",
			"19.1",
			"20-beta1",
		]);
		expect(ahead.latest?.tag).toBe("19.1");
		expect(ahead.prerelease?.tag).toBe("20-beta1");
		expect(ahead.prerelease?.version?.canonical).toBe("20b1");
	});

	test("compares a build counter numerically", () => {
		const selection = newest(shapeOf("server-cuda-b9843") as TagShape, [
			"latest",
			"server-cuda-latest",
			"server-b9843",
			"server-cuda-b9843",
			"server-cuda-b9999",
			"server-cuda-b10412",
		]);
		// a string comparison would stop at b9999
		expect(selection.latest?.tag).toBe("server-cuda-b10412");
		expect(selection.how).toBe("build");
		// a build tag under a different prefix is a different variant
		expect(selection.all.map(({ tag }) => tag)).not.toContain("server-b9843");
	});

	test("has no answer when nothing upstream fits the template", () => {
		const selection = newest(shapeOf("18.3") as TagShape, ["latest", "trixie"]);
		expect(selection.latest).toBeUndefined();
		expect(selection.how).toBe("none");
		expect(selection.all).toEqual([]);
	});
});
