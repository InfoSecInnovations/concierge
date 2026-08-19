import { describe, expect, test } from "bun:test";
import { dependents, readPackages } from "../deps";
import { nodePackage, pythonPackage, useRepo } from "./fixture";

// case, underscores and dots all normalise away under PEP 503
const NORMALISED = `[project]
name = "python-normalised"
version = "0.1.0"
dependencies = [
    "Python_Lib",
]
`;

// an extra, a specifier and an environment marker, next to an external dependency
const MARKED = `[project]
name = "python-marked"
version = "0.1.0"
dependencies = [
    "httpx~=0.28",
    "python-lib[extra]>=0.1.0 ; python_version > '3.12'",
]
`;

describe("dependency links", () => {
	const repo = useRepo({
		packages: [
			pythonPackage("python-lib", "0.1.0"),
			pythonPackage("python-tool", "0.1.0"),
			// the container shape: named without a version, resolved by path
			pythonPackage("python-app", "0.1.0", { deps: { "python-lib": null } }),
			pythonPackage("python-client", "0.1.0", {
				deps: { "python-lib": "0.1.0" },
				devDeps: { "python-tool": "0.1.0" },
			}),
			pythonPackage("python-indirect", "0.1.0", {
				deps: { "python-client": null },
			}),
			pythonPackage("python-normalised", "0.1.0", {
				files: { "pyproject.toml": NORMALISED },
			}),
			pythonPackage("python-marked", "0.1.0", {
				files: { "pyproject.toml": MARKED },
			}),
			nodePackage("node-lib", "0.1.0"),
			nodePackage("node-app", "0.1.0", { deps: { "node-lib": "workspace:*" } }),
			nodePackage("node-dev", "0.1.0", {
				devDeps: { "node-lib": "workspace:*" },
			}),
			nodePackage("node-standalone", "0.1.0"),
			// the same distribution name on both sides, as the two api clients are
			nodePackage("shared-name", "0.1.0"),
			nodePackage("node-shares", "0.1.0", { deps: { "shared-name": "0.1.0" } }),
			pythonPackage("shared-name", "0.1.0"),
			pythonPackage("python-shares", "0.1.0", {
				deps: { "shared-name": null },
			}),
		],
	});

	const read = () => readPackages(repo.dir, repo.paths);

	test("finds pinned, unpinned, normalised and marked dependents", async () => {
		expect(dependents(await read(), "python_lib").sort()).toEqual([
			"python_app",
			"python_client",
			"python_marked",
			"python_normalised",
		]);
	});

	test("counts a python dev group dependency", async () => {
		expect(dependents(await read(), "python_tool")).toEqual(["python_client"]);
	});

	test("counts node dependencies and devDependencies", async () => {
		expect(dependents(await read(), "node-lib").sort()).toEqual([
			"node-app",
			"node-dev",
		]);
	});

	test("returns nothing for a package no one names", async () => {
		expect(dependents(await read(), "node-standalone")).toEqual([]);
	});

	test("goes one hop, leaving the cascade to the caller", async () => {
		const packages = await read();
		expect(dependents(packages, "python_lib")).not.toContain("python_indirect");
		expect(dependents(packages, "python_client")).toEqual(["python_indirect"]);
	});

	test("keeps the ecosystems apart", async () => {
		const packages = await read();
		expect(dependents(packages, "shared_name")).toEqual(["python_shares"]);
		expect(dependents(packages, "shared-name")).toEqual(["node-shares"]);
	});

	test("records the manifest, type, dist name and resolved edges", async () => {
		const packages = await read();
		expect(packages.find((pkg) => pkg.path === "python_client")).toEqual({
			path: "python_client",
			manifest: "python_client/pyproject.toml",
			type: "python",
			name: "python-client",
			dependsOn: ["python_lib", "python_tool"],
		});
	});

	test("drops dependencies that are not one of the packages", async () => {
		const marked = (await read()).find((pkg) => pkg.path === "python_marked");
		expect(marked?.dependsOn).toEqual(["python_lib"]);
	});

	test("throws for a path it was not given", async () => {
		const packages = await read();
		// a distribution name is not a path
		expect(() => dependents(packages, "python-lib")).toThrow(
			/not one of the packages/,
		);
	});

	test("throws for a directory with no manifest", async () => {
		await expect(readPackages(repo.dir, ["nothing-here"])).rejects.toThrow(
			/no package.json or pyproject.toml/,
		);
	});
});

describe("a manifest with no name", () => {
	const repo = useRepo({
		packages: [
			pythonPackage("python-nameless", "0.1.0", {
				files: { "pyproject.toml": '[project]\nversion = "0.1.0"\n' },
			}),
		],
	});

	test("throws rather than becoming a package nothing can name", async () => {
		await expect(readPackages(repo.dir, repo.paths)).rejects.toThrow(
			/no name declared/,
		);
	});
});
