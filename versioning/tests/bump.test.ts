import { describe, expect, test } from "bun:test";
import { join } from "node:path";
import { bump } from "../bump";
import { nodePackage, pythonPackage, released, useRepo } from "./fixture";

describe("a release that touches four components", () => {
	const repo = useRepo({
		root: "0.8.0",
		packages: [
			nodePackage("node-lib", "0.1.0"),
			nodePackage("node-exact", "0.2.0", { deps: { "node-lib": "0.1.0" } }),
			pythonPackage("python-lib", "0.3.0"),
			// the container shape, named without a version
			pythonPackage("python-container", "0.4.0", {
				deps: { "python-lib": null },
			}),
			// the api client shape, pinned with ==
			pythonPackage("python-client", "0.6.0", {
				deps: { "python-lib": "0.3.0" },
			}),
			nodePackage("node-quiet", "0.5.0"),
		],
		releases: [released("0.8.0")],
		touch: ["node-lib", "python-lib"],
	});

	const run = (dryRun?: boolean) =>
		bump({
			repoDir: repo.dir,
			paths: repo.paths,
			releaseType: "minor",
			dryRun,
		});

	test("writes every affected version, and moves the root by one", async () => {
		const report = await run();
		// four components moved, the root still only goes up one minor
		expect(report.root).toBe("0.9.0");
		expect(
			report.bumps.map(({ path, current, next }) => [path, current, next]),
		).toEqual([
			["node-lib", "0.1.0", "0.2.0"],
			["node-exact", "0.2.0", "0.3.0"],
			["python_lib", "0.3.0", "0.4.0"],
			["python_container", "0.4.0", "0.5.0"],
			["python_client", "0.6.0", "0.7.0"],
		]);
		expect(await repo.versionOf("node-lib")).toBe("0.2.0");
		expect(await repo.versionOf("python-container")).toBe("0.5.0");
		expect(await repo.read("package.json")).toContain('"version": "0.9.0"');
	});

	test("leaves a package nothing reaches alone", async () => {
		await run();
		expect(await repo.versionOf("node-quiet")).toBe("0.5.0");
	});

	test("moves the pins that name a bumped package", async () => {
		await run();
		const manifest = await repo.read("node-exact/package.json");
		expect(JSON.parse(manifest).dependencies).toEqual({ "node-lib": "0.2.0" });
		expect(await repo.read("python_client/pyproject.toml")).toContain(
			'"python-lib==0.4.0"',
		);
	});

	test("reports exactly the files it wrote", async () => {
		expect((await run()).files).toEqual([
			"node-exact/package.json",
			"node-lib/package.json",
			"package.json",
			"python_client/pyproject.toml",
			"python_container/pyproject.toml",
			"python_lib/pyproject.toml",
		]);
	});

	test("writes nothing on a dry run", async () => {
		const report = await run(true);
		expect(report.files).toEqual([]);
		expect(report.root).toBe("0.9.0");
		expect(report.bumps).toHaveLength(5);
		expect((await repo.git("status", "--porcelain")).stdout).toBe("");
	});
});

describe("a release with nothing to bump", () => {
	const repo = useRepo({
		root: "0.8.0",
		packages: [nodePackage("node-quiet", "0.1.0")],
		releases: [released("0.8.0")],
	});

	test("refuses, rather than moving the root on its own", async () => {
		await expect(
			bump({ repoDir: repo.dir, paths: repo.paths, releaseType: "minor" }),
		).rejects.toThrow(/nothing changed/);
		expect((await repo.git("status", "--porcelain")).stdout).toBe("");
	});
});

describe("promoting the root with no component changes", () => {
	const repo = useRepo({
		root: "0.9.0-rc.1",
		packages: [nodePackage("node-quiet", "0.1.0")],
		releases: [released("0.9.0-rc.1")],
	});

	test("releases the root and leaves the components stable", async () => {
		const report = await bump({
			repoDir: repo.dir,
			paths: repo.paths,
			releaseType: "release",
		});
		expect(report).toMatchObject({ root: "0.9.0", bumps: [] });
		expect(report.files).toEqual(["package.json"]);
		expect(await repo.versionOf("node-quiet")).toBe("0.1.0");
	});
});

describe("a release the versions refuse", () => {
	const repo = useRepo({
		root: "0.9.0-rc.1",
		packages: [
			nodePackage("node-changed", "0.3.0"),
			nodePackage("node-user", "0.4.0", { deps: { "node-changed": "0.3.0" } }),
		],
		releases: [released("0.9.0-rc.1")],
		touch: ["node-changed"],
	});

	test("propagates every refusal without writing", async () => {
		await expect(
			bump({ repoDir: repo.dir, paths: repo.paths, releaseType: "release" }),
		).rejects.toThrow(
			/node-changed: 0\.3\.0 is already a release; node-user: 0\.4\.0 is already a release/,
		);
		expect((await repo.git("status", "--porcelain")).stdout).toBe("");
	});
});

describe("the command line", () => {
	const repo = useRepo({
		root: "0.8.0",
		packages: [nodePackage("node-lib", "0.1.0")],
		releases: [released("0.8.0")],
		touch: ["node-lib"],
	});
	const script = join(import.meta.dir, "..", "bump.ts");

	const spawn = (args: string[], env?: Record<string, string>) =>
		Bun.spawn(["bun", script, ...args], {
			cwd: repo.dir,
			env: { ...process.env, ...env },
			stdout: "pipe",
			stderr: "pipe",
		});

	test("prints the report and writes the workflow outputs", async () => {
		const outputFile = join(repo.dir, "outputs.txt");
		const proc = spawn(["--release-type", "minor", "--paths", "node-lib"], {
			GITHUB_OUTPUT: outputFile,
		});
		const stdout = await new Response(proc.stdout).text();
		expect(await proc.exited).toBe(0);
		expect(JSON.parse(stdout)).toEqual({
			root: "0.9.0",
			bumps: [
				{
					path: "node-lib",
					name: "node-lib",
					current: "0.1.0",
					next: "0.2.0",
				},
			],
			files: ["node-lib/package.json", "package.json"],
		});
		expect(await Bun.file(outputFile).text()).toBe(
			"root-version=0.9.0\nbumped=true\ntouched-files<<FILES\nnode-lib/package.json\npackage.json\nFILES\n",
		);
	});

	test("refuses a release type it does not know", async () => {
		const proc = spawn(["--release-type", "huge", "--paths", "node-lib"]);
		const stderr = await new Response(proc.stderr).text();
		expect(await proc.exited).not.toBe(0);
		expect(stderr).toContain("release-type");
	});
});
