import { describe, expect, test } from "bun:test";
import { planBumps } from "../plan";
import { nodePackage, pythonPackage, released, useRepo } from "./fixture";

describe("a release that touches a dependency chain", () => {
	const repo = useRepo({
		packages: [
			nodePackage("node-base", "0.1.0"),
			nodePackage("node-mid", "0.2.0", {
				deps: { "node-base": "workspace:*" },
			}),
			nodePackage("node-top", "1.0.0", { deps: { "node-mid": "workspace:*" } }),
			nodePackage("node-side", "0.3.0", {
				devDeps: { "node-base": "workspace:*" },
			}),
			nodePackage("node-alone", "0.5.0"),
			pythonPackage("python-lib", "0.2.0"),
			pythonPackage("python-app", "0.1.0", { deps: { "python-lib": null } }),
			pythonPackage("python-quiet", "0.4.0"),
		],
		releases: [released("0.1.0")],
		touch: ["node-base", "python-lib"],
	});

	const plan = () => planBumps(repo.dir, repo.paths, "minor");

	test("picks up every affected package and nothing else", async () => {
		expect((await plan()).map(({ path }) => path)).toEqual([
			"node-base",
			"node-mid",
			"node-top",
			"node-side",
			"python_lib",
			"python_app",
		]);
	});

	test("reports the version each package will be written to", async () => {
		expect(
			(await plan()).map(({ path, current, next }) => [path, current, next]),
		).toEqual([
			["node-base", "0.1.0", "0.2.0"],
			["node-mid", "0.2.0", "0.3.0"],
			// reached through node-mid, which nothing changed directly
			["node-top", "1.0.0", "1.1.0"],
			["node-side", "0.3.0", "0.4.0"],
			["python_lib", "0.2.0", "0.3.0"],
			["python_app", "0.1.0", "0.2.0"],
		]);
	});

	test("distinguishes a direct change from a dependency link", async () => {
		const reasons = Object.fromEntries(
			(await plan()).map(({ path, reason }) => [path, reason]),
		);
		expect(reasons).toEqual({
			"node-base": "changed",
			"node-mid": "dependency",
			"node-top": "dependency",
			"node-side": "dependency",
			python_lib: "changed",
			python_app: "dependency",
		});
	});

	test("carries what the writers will need", async () => {
		expect((await plan()).find(({ path }) => path === "python_app")).toEqual({
			path: "python_app",
			manifest: "python_app/pyproject.toml",
			type: "python",
			name: "python-app",
			current: "0.1.0",
			next: "0.2.0",
			reason: "dependency",
		});
	});

	test("only follows links between the paths it was given", async () => {
		const paths = repo.paths.filter((path) => path !== "node-mid");
		const bumps = await planBumps(repo.dir, paths, "minor");
		// node-top only depends on node-base through node-mid, which is not in the graph
		expect(bumps.map(({ path }) => path)).toEqual([
			"node-base",
			"node-side",
			"python_lib",
			"python_app",
		]);
	});

	test("counts a version that was never committed as a change", async () => {
		const manifest = "node-alone/package.json";
		const text = await repo.read(manifest);
		await repo.write(manifest, text.replace("0.5.0", "0.6.0"));
		const alone = (await plan()).find(({ path }) => path === "node-alone");
		expect(alone).toMatchObject({
			current: "0.6.0",
			next: "0.7.0",
			reason: "changed",
		});
	});
});

describe("a release with nothing to do", () => {
	const repo = useRepo({
		packages: [
			nodePackage("node-quiet", "0.1.0"),
			nodePackage("node-user", "0.2.0", {
				deps: { "node-quiet": "workspace:*" },
			}),
		],
		releases: [released("0.1.0")],
	});

	test("returns an empty list", async () => {
		expect(await planBumps(repo.dir, repo.paths, "minor")).toEqual([]);
	});
});

describe("a dependency cycle", () => {
	const repo = useRepo({
		packages: [
			nodePackage("node-a", "0.1.0", { deps: { "node-b": "workspace:*" } }),
			nodePackage("node-b", "0.2.0", { deps: { "node-a": "workspace:*" } }),
		],
		releases: [released("0.1.0")],
		touch: ["node-a"],
	});

	test("visits each package once", async () => {
		const bumps = await planBumps(repo.dir, repo.paths, "minor");
		expect(bumps.map(({ path }) => path)).toEqual(["node-a", "node-b"]);
	});
});

describe("a release the versions refuse", () => {
	const repo = useRepo({
		packages: [
			nodePackage("node-pre", "0.2.0-alpha.0"),
			nodePackage("node-stable", "0.3.0", {
				deps: { "node-pre": "workspace:*" },
			}),
			nodePackage("node-also-stable", "0.4.0", {
				deps: { "node-pre": "workspace:*" },
			}),
		],
		releases: [released("0.1.0")],
		touch: ["node-pre"],
	});

	test("refuses a release for the stable packages a link pulled in", async () => {
		await expect(planBumps(repo.dir, repo.paths, "release")).rejects.toThrow(
			/^cannot release: node-stable: 0\.3\.0 is already a release; node-also-stable: 0\.4\.0 is already a release$/,
		);
	});

	test("still plans the release when only the prerelease is affected", async () => {
		const bumps = await planBumps(repo.dir, ["node-pre"], "release");
		expect(bumps).toMatchObject([{ current: "0.2.0-alpha.0", next: "0.2.0" }]);
	});
});
