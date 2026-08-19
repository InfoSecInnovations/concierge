import { describe, expect, test } from "bun:test";
import { versionCommit } from "../history";
import {
	type Repo,
	nodePackage,
	pythonPackage,
	released,
	useRepo,
} from "./fixture";

/** reads through the handle on each call, so it works with the object useRepo repopulates */
const revision = (repo: Repo) => async (rev: string) =>
	(await repo.git("rev-parse", rev)).stdout.trim();

const contentAt = (repo: Repo) => async (rev: string, file: string) =>
	(await repo.git("show", `${rev}:${file}`)).stdout;

describe("versions bumped at different releases", () => {
	const repo = useRepo({
		packages: [
			pythonPackage("python-bumped", "0.2.0"),
			nodePackage("node-bumped", "0.3.0"),
		],
		releases: [
			released("0.1.0", {
				versions: { "python-bumped": "0.1.0", "node-bumped": "0.1.0" },
				touch: ["python-bumped", "node-bumped"],
			}),
			// python-bumped reaches the version it still declares
			released("0.2.0", { versions: { "node-bumped": "0.2.0" } }),
			// node-bumped reaches its, while python-bumped only changes source
			released("0.3.0", { touch: ["python-bumped"] }),
		],
	});
	const sha = revision(repo);
	const at = contentAt(repo);

	test("finds the commit that set the version", async () => {
		expect(await versionCommit(repo.dir, "python_bumped")).toBe(
			await sha("v0.2.0"),
		);
	});

	test("finds a commit where the version changed from another version", async () => {
		const commit = await versionCommit(repo.dir, "python_bumped");
		const manifest = "python_bumped/pyproject.toml";
		expect(await at(`${commit}`, manifest)).toContain('version = "0.2.0"');
		expect(await at(`${commit}^`, manifest)).toContain('version = "0.1.0"');
	});

	test("ignores later commits that only changed the package's source", async () => {
		// the directory really did change after the bump, the version did not
		const diff = await repo.git(
			"diff",
			"--quiet",
			"v0.2.0",
			"v0.3.0",
			"--",
			"python_bumped",
		);
		expect(diff.exitCode).toBe(1);
		expect(await versionCommit(repo.dir, "python_bumped")).not.toBe(
			await sha("v0.3.0"),
		);
	});

	test("resolves each package against its own history", async () => {
		expect(await versionCommit(repo.dir, "node-bumped")).toBe(
			await sha("v0.3.0"),
		);
		const manifest = "node-bumped/package.json";
		const commit = await versionCommit(repo.dir, "node-bumped");
		expect(await at(`${commit}`, manifest)).toContain('"version": "0.3.0"');
		expect(await at(`${commit}^`, manifest)).toContain('"version": "0.2.0"');
	});
});

describe("a version adopted, dropped and adopted again", () => {
	const repo = useRepo({
		packages: [pythonPackage("python-rolled-back", "0.1.0")],
		releases: [
			released("0.1.0", { versions: { "python-rolled-back": "0.1.0" } }),
			released("0.2.0", { versions: { "python-rolled-back": "0.2.0" } }),
			released("0.3.0", { versions: { "python-rolled-back": "0.1.0" } }),
		],
	});
	const sha = revision(repo);

	test("finds the most recent adoption", async () => {
		expect(await versionCommit(repo.dir, "python_rolled_back")).toBe(
			await sha("v0.3.0"),
		);
	});
});

describe("a package that never bumped", () => {
	const repo = useRepo({
		packages: [
			nodePackage("node-added", "0.1.0"),
			nodePackage("node-first", "0.1.0"),
		],
		releases: [
			released("0.1.0", { absent: ["node-added"] }),
			released("0.2.0"),
		],
	});
	const sha = revision(repo);

	test("finds the commit that added the manifest", async () => {
		const commit = await versionCommit(repo.dir, "node-added");
		expect(commit).toBe(await sha("v0.2.0"));
		// there is no earlier version to have changed from: the file did not exist
		expect(
			(await repo.git("show", `${commit}^:node-added/package.json`)).exitCode,
		).not.toBe(0);
	});

	test("finds the root commit for a package that was there from the start", async () => {
		expect(await versionCommit(repo.dir, "node-first")).toBe(
			await sha("v0.1.0"),
		);
		expect((await repo.git("rev-parse", "v0.1.0^")).exitCode).not.toBe(0);
	});
});

describe("state that was never committed", () => {
	const repo = useRepo({
		packages: [pythonPackage("python-dirty", "0.1.0")],
		releases: [released("0.1.0")],
	});

	test("returns null for a version only the working tree declares", async () => {
		const manifest = "python_dirty/pyproject.toml";
		const text = await repo.read(manifest);
		await repo.write(manifest, text.replace("0.1.0", "0.2.0"));
		expect(await versionCommit(repo.dir, "python_dirty")).toBeNull();
	});

	test("returns null for a manifest that was never committed", async () => {
		await repo.write(
			"node-untracked/package.json",
			'{\n\t"name": "node-untracked",\n\t"version": "0.1.0"\n}\n',
		);
		expect(await versionCommit(repo.dir, "node-untracked")).toBeNull();
	});

	test("throws for a directory with no manifest", async () => {
		await repo.write("node-empty/readme.md", "");
		await expect(versionCommit(repo.dir, "node-empty")).rejects.toThrow(
			/no package.json or pyproject.toml/,
		);
	});
});

describe("a manifest with no version", () => {
	const repo = useRepo({
		packages: [
			pythonPackage("python-broken", "0.1.0", {
				files: { "pyproject.toml": "not a manifest\n" },
			}),
		],
		releases: [released("0.1.0")],
	});

	test("throws rather than reporting no baseline", async () => {
		await expect(versionCommit(repo.dir, "python_broken")).rejects.toThrow(
			/no version declared/,
		);
	});
});
