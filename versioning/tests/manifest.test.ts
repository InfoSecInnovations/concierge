import { describe, expect, test } from "bun:test";
import { manifestIn, versionIn } from "../manifest";
import { nodePackage, pythonPackage, useRepo } from "./fixture";

describe("manifestIn", () => {
	const repo = useRepo({
		packages: [
			nodePackage("node-both", "0.1.0"),
			pythonPackage("python-only", "0.1.0"),
			pythonPackage("python-nested", "0.1.0", { dir: "containers/nested" }),
		],
	});

	test("finds a package.json", async () => {
		expect(await manifestIn(repo.dir, "node-both")).toBe(
			"node-both/package.json",
		);
	});

	test("finds a pyproject.toml", async () => {
		expect(await manifestIn(repo.dir, "python_only")).toBe(
			"python_only/pyproject.toml",
		);
	});

	test("prefers package.json where a directory has both", async () => {
		await repo.write(
			"node-both/pyproject.toml",
			'[project]\nversion = "9.9.9"\n',
		);
		expect(await manifestIn(repo.dir, "node-both")).toBe(
			"node-both/package.json",
		);
	});

	test("keeps nested paths posix, for git", async () => {
		expect(await manifestIn(repo.dir, "containers/nested")).toBe(
			"containers/nested/pyproject.toml",
		);
	});

	test("throws where a directory has neither", async () => {
		await expect(manifestIn(repo.dir, "nothing-here")).rejects.toThrow(
			/no package.json or pyproject.toml/,
		);
	});
});

describe("versionIn", () => {
	test("reads a package.json", () => {
		expect(versionIn("a/package.json", '{ "version": "1.2.3" }')).toBe("1.2.3");
	});

	test("reads a pyproject.toml", () => {
		expect(
			versionIn(
				"a/pyproject.toml",
				'[project]\nname = "a"\nversion = "1.2.3"\n',
			),
		).toBe("1.2.3");
	});

	test("takes the first top level version of a pyproject.toml", () => {
		expect(
			versionIn(
				"a/pyproject.toml",
				'[project]\nversion = "1.2.3"\n\n[tool.other]\nversion = "9.9.9"\n',
			),
		).toBe("1.2.3");
	});

	test("returns null when there is no version", () => {
		expect(versionIn("a/package.json", '{ "name": "a" }')).toBeNull();
		expect(versionIn("a/pyproject.toml", '[project]\nname = "a"\n')).toBeNull();
	});

	test("returns null for text that does not parse", () => {
		expect(versionIn("a/package.json", "not a manifest")).toBeNull();
	});

	test("throws for a file it does not know how to read", () => {
		expect(() => versionIn("a/setup.cfg", "")).toThrow(/not a package.json/);
	});
});
