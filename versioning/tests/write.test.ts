import { describe, expect, test } from "bun:test";
import { rewritePins, writeVersion } from "../write";
import { nodePackage, pythonPackage, released, useRepo } from "./fixture";

// no trailing newline, as shabti_util's pyproject.toml has none
const TERSE = '[project]\nname = "python-terse"\nversion = "0.1.0"';

// a pin spelled with an underscore and a capital, which PEP 503 says is the same name
const UNDERSCORED = `[project]
name = "python-underscored"
version = "0.1.0"
dependencies = [
    "Python_Lib==0.1.0",
]
`;

// the legacy shape, and again without a trailing newline
const REQUIREMENTS = "python-lib==0.1.0\nhttpx~=0.28\npython-other==0.1.0";

describe("writeVersion", () => {
	const repo = useRepo({
		packages: [
			nodePackage("node-writable", "0.1.0", {
				deps: { "node-dep": "workspace:*" },
			}),
			nodePackage("node-dep", "0.1.0"),
			pythonPackage("python-writable", "0.1.0"),
			pythonPackage("python-terse", "0.1.0", {
				files: { "pyproject.toml": TERSE },
			}),
		],
		releases: [released("0.1.0")],
	});

	test("writes a node version, leaving the manifest shape alone", async () => {
		expect(
			await writeVersion(repo.dir, "node-writable", "0.1.0", "0.2.0"),
		).toBe("node-writable/package.json");
		const manifest = await repo.read("node-writable/package.json");
		expect(manifest.trimEnd()).toEndWith('\t"version": "0.2.0"\n}');
		expect(JSON.parse(manifest).dependencies).toEqual({
			"node-dep": "workspace:*",
		});
		expect(await repo.versionOf("node-writable")).toBe("0.2.0");
	});

	test("neither commits nor tags", async () => {
		const log = (await repo.git("log", "--oneline")).stdout;
		await writeVersion(repo.dir, "node-writable", "0.1.0", "0.2.0");
		expect((await repo.git("log", "--oneline")).stdout).toBe(log);
		expect(await repo.tags()).toEqual(["v0.1.0"]);
	});

	test("writes a python version, changing only that line", async () => {
		const before = await repo.read("python_writable/pyproject.toml");
		expect(
			await writeVersion(repo.dir, "python_writable", "0.1.0", "0.2.0"),
		).toBe("python_writable/pyproject.toml");
		expect(await repo.read("python_writable/pyproject.toml")).toBe(
			before.replace('version = "0.1.0"', 'version = "0.2.0"'),
		);
	});

	test("keeps a manifest that has no trailing newline", async () => {
		await writeVersion(repo.dir, "python_terse", "0.1.0", "0.2.0");
		expect(await repo.read("python_terse/pyproject.toml")).toBe(
			TERSE.replace("0.1.0", "0.2.0"),
		);
	});

	test("refuses to write when the tree moved underneath the plan", async () => {
		await expect(
			writeVersion(repo.dir, "python_writable", "0.9.0", "1.0.0"),
		).rejects.toThrow(/declares 0\.1\.0, expected 0\.9\.0/);
		expect(await repo.versionOf("python-writable")).toBe("0.1.0");
	});
});

describe("rewritePins", () => {
	const repo = useRepo({
		packages: [
			pythonPackage("python-lib", "0.1.0"),
			pythonPackage("python-tool", "0.1.0"),
			// the api client shape: a pin in dependencies and another in the dev group
			pythonPackage("python-client", "0.1.0", {
				deps: { "python-lib": "0.1.0" },
				devDeps: { "python-tool": "0.1.0" },
			}),
			// the container shape: named without a version, so there is nothing to rewrite
			pythonPackage("python-container", "0.1.0", {
				deps: { "python-lib": null },
			}),
			pythonPackage("python-underscored", "0.1.0", {
				files: { "pyproject.toml": UNDERSCORED },
			}),
			pythonPackage("python-legacy", "0.1.0", {
				files: { "requirements.txt": REQUIREMENTS },
			}),
			nodePackage("node-lib", "0.1.0"),
			nodePackage("node-workspace", "0.1.0", {
				deps: { "node-lib": "workspace:*" },
			}),
			nodePackage("node-exact", "0.1.0", { deps: { "node-lib": "0.1.0" } }),
			nodePackage("node-ranged", "0.1.0", { deps: { "node-lib": "^0.1.0" } }),
		],
		releases: [released("0.1.0")],
	});

	const lib = { name: "python-lib", current: "0.1.0", next: "0.2.0" };
	const tool = { name: "python-tool", current: "0.1.0", next: "0.3.0" };
	const nodeLib = { name: "node-lib", current: "0.1.0", next: "0.2.0" };

	test("rewrites a pin in dependencies and one in a dev group, in one pass", async () => {
		const changed = await rewritePins(repo.dir, [lib, tool]);
		expect(changed.filter((file) => file.startsWith("python_client/"))).toEqual(
			["python_client/pyproject.toml"],
		);
		const manifest = await repo.read("python_client/pyproject.toml");
		expect(manifest).toContain('"python-lib==0.2.0"');
		expect(manifest).toContain('"python-tool==0.3.0"');
	});

	test("leaves a dependency that names no version alone", async () => {
		const changed = await rewritePins(repo.dir, [lib]);
		expect(changed).not.toContain("python_container/pyproject.toml");
		expect(await repo.read("python_container/pyproject.toml")).toContain(
			'"python-lib",',
		);
	});

	test("rewrites an exact node pin, and only that", async () => {
		expect(await rewritePins(repo.dir, [nodeLib])).toEqual([
			"node-exact/package.json",
		]);
		const dependencies = async (dir: string) =>
			JSON.parse(await repo.read(`${dir}/package.json`)).dependencies;
		expect(await dependencies("node-exact")).toEqual({ "node-lib": "0.2.0" });
		expect(await dependencies("node-workspace")).toEqual({
			"node-lib": "workspace:*",
		});
		expect(await dependencies("node-ranged")).toEqual({
			"node-lib": "^0.1.0",
		});
	});

	test("rewrites a requirements line, keeping the rest byte for byte", async () => {
		await rewritePins(repo.dir, [lib]);
		expect(await repo.read("python_legacy/requirements.txt")).toBe(
			REQUIREMENTS.replace("python-lib==0.1.0", "python-lib==0.2.0"),
		);
	});

	test("matches a pin whose separators and case differ", async () => {
		await rewritePins(repo.dir, [lib]);
		expect(await repo.read("python_underscored/pyproject.toml")).toContain(
			'"Python_Lib==0.2.0"',
		);
	});

	test("leaves packages that are not being bumped alone", async () => {
		await rewritePins(repo.dir, [lib]);
		expect(await repo.read("python_legacy/requirements.txt")).toContain(
			"python-other==0.1.0",
		);
		expect(await repo.read("python_client/pyproject.toml")).toContain(
			'"python-tool==0.1.0"',
		);
	});

	test("refuses a pin that has drifted, without writing anything", async () => {
		const before = await repo.read("python_client/pyproject.toml");
		await expect(
			rewritePins(repo.dir, [{ ...lib, current: "0.9.0", next: "1.0.0" }]),
		).rejects.toThrow(/pins python-lib at 0\.1\.0, but it declares 0\.9\.0/);
		expect(await repo.read("python_client/pyproject.toml")).toBe(before);
		expect((await repo.git("status", "--porcelain")).stdout).toBe("");
	});

	test("returns nothing for an empty bump list", async () => {
		expect(await rewritePins(repo.dir, [])).toEqual([]);
	});
});
