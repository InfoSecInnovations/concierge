import { describe, expect, test } from "bun:test";
import { existsSync } from "node:fs";
import {
	createRepo,
	nodePackage,
	pythonPackage,
	released,
	useRepo,
} from "./fixture";

describe("a repo with history", () => {
	const repo = useRepo({
		root: "0.3.0",
		packages: [
			pythonPackage("python-pinned", "0.2.0", {
				deps: { "python-lib": "0.2.0" },
			}),
			pythonPackage("python-lib", "0.2.0"),
			pythonPackage("python-unpinned", "0.1.0", {
				dir: "containers/python_unpinned",
				deps: { "python-lib": null },
			}),
			nodePackage("node-workspace", "0.2.0", {
				deps: { "node-lib": "workspace:*" },
			}),
			nodePackage("node-lib", "0.1.0"),
		],
		releases: [
			released("0.1.0", {
				absent: ["node-workspace"],
				versions: {
					"python-pinned": "0.1.0",
					"python-lib": "0.1.0",
				},
				touch: ["python-pinned", "python-lib", "python-unpinned", "node-lib"],
			}),
			released("0.2.0", { touch: ["python-pinned", "python-lib"] }),
		],
		touch: ["node-lib"],
		tags: ["legacy-1.0", "launcher-v0.4.0"],
	});

	const changed = async (dir: string, tag: string) =>
		(await repo.git("diff", "--quiet", tag, "--", dir)).exitCode !== 0;

	const at = async (tag: string, file: string) => {
		const { exitCode, stdout } = await repo.git("show", `${tag}:${file}`);
		expect(exitCode).toBe(0);
		return stdout;
	};

	test("tags each release with the prefix, alongside the raw tags", async () => {
		expect((await repo.tags()).sort()).toEqual([
			"launcher-v0.4.0",
			"legacy-1.0",
			"v0.1.0",
			"v0.2.0",
		]);
	});

	test("lists the package directories as paths", () => {
		expect(repo.paths).toEqual([
			"python_pinned",
			"python_lib",
			"containers/python_unpinned",
			"node-workspace",
			"node-lib",
		]);
	});

	test("records the version each release declared", async () => {
		expect(await at("v0.1.0", "python_pinned/pyproject.toml")).toContain(
			'version = "0.1.0"',
		);
		expect(await at("v0.2.0", "python_pinned/pyproject.toml")).toContain(
			'version = "0.2.0"',
		);
		expect(await repo.versionOf("python-pinned")).toBe("0.2.0");
	});

	test("carries the current version into releases that do not override it", async () => {
		const manifest = await at(
			"v0.1.0",
			"containers/python_unpinned/pyproject.toml",
		);
		expect(manifest).toContain('version = "0.1.0"');
	});

	test("moves the root version with each release", async () => {
		expect(await at("v0.1.0", "package.json")).toContain('"version": "0.1.0"');
		expect(await repo.read("package.json")).toContain('"version": "0.3.0"');
	});

	test("omits packages that were absent at a release", async () => {
		expect(
			(await repo.git("show", "v0.1.0:node-workspace/package.json")).exitCode,
		).not.toBe(0);
		expect(await at("v0.2.0", "node-workspace/package.json")).toContain(
			'"version": "0.2.0"',
		);
	});

	test("diffs a change made after the last release", async () => {
		expect(await changed("node-lib", "v0.2.0")).toBe(true);
		expect(await changed("python_pinned", "v0.2.0")).toBe(false);
	});

	test("diffs a change made in an earlier release", async () => {
		expect(await changed("python_pinned", "v0.1.0")).toBe(true);
		expect(await changed("python_lib", "v0.1.0")).toBe(true);
		expect(await changed("node-workspace", "v0.1.0")).toBe(true);
	});

	test("reports no diff for a package that never changed", async () => {
		expect(await changed("containers/python_unpinned", "v0.1.0")).toBe(false);
	});

	test("pins python dependencies and points uv at the dependency directory", async () => {
		const manifest = await repo.read("python_pinned/pyproject.toml");
		expect(manifest).toContain('"python-lib==0.2.0",');
		expect(manifest).toContain(
			'python-lib = { path = "../python_lib", editable = true }',
		);
	});

	test("declares an unpinned python dependency by name only", async () => {
		const manifest = await repo.read(
			"containers/python_unpinned/pyproject.toml",
		);
		expect(manifest).toContain('"python-lib",');
		expect(manifest).not.toContain("==");
		expect(manifest).toContain(
			'python-lib = { path = "../../python_lib", editable = true }',
		);
	});

	test("keeps node dependency specifiers verbatim", async () => {
		const manifest = JSON.parse(await repo.read("node-workspace/package.json"));
		expect(manifest.dependencies).toEqual({ "node-lib": "workspace:*" });
		expect(await repo.versionOf("node-workspace")).toBe("0.2.0");
	});

	test("keeps version as the last key of a package.json, under one tab", async () => {
		const manifest = await repo.read("node-lib/package.json");
		expect(manifest).toEndWith('\t"version": "0.1.0"\n}\n');
		// the regex the tool's package.json writer anchors on
		const match = /^\t"version"\s*:\s*"(?<value>[^"]+)"/m.exec(manifest);
		expect(match?.groups?.value).toBe("0.1.0");
	});

	test("leaves the working tree clean", async () => {
		expect((await repo.git("status", "--porcelain")).stdout).toBe("");
	});
});

describe("a repo without releases", () => {
	const repo = useRepo({
		packages: [
			nodePackage("no-baseline", "0.1.0", { files: { "extra.txt": "x" } }),
		],
	});

	test("has no tags and a default root version", async () => {
		expect(await repo.tags()).toEqual([]);
		expect(await repo.read("package.json")).toContain('"version": "0.1.0"');
	});

	test("still commits, so there is something to diff against", async () => {
		expect((await repo.git("rev-parse", "HEAD")).exitCode).toBe(0);
	});

	test("writes raw files alongside the manifest", async () => {
		expect(await repo.read("no-baseline/extra.txt")).toBe("x");
	});
});

describe("a repo with an interleaved prerelease", () => {
	const repo = useRepo({
		tagPrefix: "shabti-v",
		root: "0.3.0-alpha.1",
		packages: [pythonPackage("python-branchy", "0.3.0a1")],
		releases: [
			released("0.3.0-alpha.0", { versions: { "python-branchy": "0.3.0a0" } }),
			// tagged later but lower: a fix released while the prerelease was in flight
			released("0.2.1", { versions: { "python-branchy": "0.2.1" } }),
		],
	});

	test("honours the tag prefix", async () => {
		expect((await repo.tags()).sort()).toEqual([
			"shabti-v0.2.1",
			"shabti-v0.3.0-alpha.0",
		]);
	});

	test("records the version each tag shipped, not the chronological one", async () => {
		const versionAt = async (tag: string) =>
			(await repo.git("show", `${tag}:python_branchy/pyproject.toml`)).stdout;
		expect(await versionAt("shabti-v0.3.0-alpha.0")).toContain(
			'version = "0.3.0a0"',
		);
		expect(await versionAt("shabti-v0.2.1")).toContain('version = "0.2.1"');
		expect(await repo.versionOf("python-branchy")).toBe("0.3.0a1");
	});
});

describe("overrides and teardown", () => {
	test("raw files are written after the manifest, so they can replace it", async () => {
		const repo = await createRepo({
			packages: [
				pythonPackage("python-malformed", "0.1.0", {
					files: { "pyproject.toml": "not a manifest\n" },
				}),
			],
		});
		expect(await repo.read("python_malformed/pyproject.toml")).toBe(
			"not a manifest\n",
		);
		await repo.cleanup();
	});

	test.skipIf(!!process.env.KEEP_FIXTURE)("cleanup removes it", async () => {
		const repo = await createRepo({
			packages: [nodePackage("throwaway", "0.1.0")],
		});
		expect(existsSync(repo.dir)).toBe(true);
		await repo.cleanup();
		expect(existsSync(repo.dir)).toBe(false);
	});
});
