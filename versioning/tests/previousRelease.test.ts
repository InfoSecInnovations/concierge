import { describe, expect, test } from "bun:test";
import { previousRelease } from "../previousRelease";
import { nodePackage, released, useRepo } from "./fixture";

describe("previousRelease", () => {
	const repo = useRepo({
		tagPrefix: "shabti-v",
		packages: [nodePackage("node-anything", "0.1.0")],
		releases: [
			released("0.8.0-rc.1"),
			released("0.8.0-rc.2"),
			released("0.8.0"),
			released("0.9.0-alpha.0"),
		],
		// the shapes the repo really holds beside its own release tags
		tags: ["shabti_launcher-v0.1.0", "v0.4.0", "shabti-vnope"],
	});

	const previous = (below: string) =>
		previousRelease(repo.dir, "shabti-v", below);

	test("takes the highest release below the version being made", async () => {
		expect(await previous("0.9.0")).toBe("shabti-v0.9.0-alpha.0");
		expect(await previous("0.9.0-alpha.0")).toBe("shabti-v0.8.0");
	});

	test("takes a prerelease when that is what precedes the version", async () => {
		expect(await previous("0.8.0")).toBe("shabti-v0.8.0-rc.2");
	});

	test("orders by semver rather than by date or by string", async () => {
		// rc10 is one identifier, which sorts above the rc.2 pair, however odd that reads
		await repo.git("tag", "shabti-v0.8.0-rc10");
		expect(await previous("0.8.0")).toBe("shabti-v0.8.0-rc10");
	});

	test("ignores other prefixes and tags that are not semver", async () => {
		expect(await previous("0.5.0")).toBeNull();
	});

	test("returns nothing when the version precedes every release", async () => {
		expect(await previous("0.1.0")).toBeNull();
	});
});
