/**
 * Builds a throwaway git repo that models the shapes the bump tool has to cope with: node and python
 * packages, pinned and unpinned dependency links, a release history with per release version overrides,
 * and source changes that git can actually see. Nothing here resolves or locks, so no network and no
 * Docker.
 */

import { afterEach, beforeEach } from "bun:test";
import { mkdtemp, readdir, rm } from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { git as gitIn, run } from "../git";

export type PackageSpec = {
	/** distribution name */
	name: string;
	type: "node" | "python";
	version: string;
	/** default: the name, with `-` -> `_` for python */
	dir?: string;
	/**
	 * dist name -> pin, or null for a dependency declared without a version. The pin is literal: it is
	 * written as given at every release, whatever version the dependency itself declares there.
	 */
	deps?: Record<string, string | null>;
	/** the same, in devDependencies for node and the `dev` dependency group for python */
	devDeps?: Record<string, string | null>;
	/** raw files, written after the manifest so they can override it */
	files?: Record<string, string>;
};

export type ReleaseSpec = {
	/** tagged `${tagPrefix}${version}`, and the root version unless `root` overrides it */
	version: string;
	root?: string;
	/** package -> the version recorded at this release */
	versions?: Record<string, string>;
	/** packages that do not exist yet at this release */
	absent?: string[];
	/** packages whose source changed in this commit */
	touch?: string[];
};

export type RepoSpec = {
	/** current root version, defaults to the last release's */
	root?: string;
	/** current state of every package */
	packages: PackageSpec[];
	/** chronological */
	releases?: ReleaseSpec[];
	/** packages whose source changed after the last release */
	touch?: string[];
	/** raw extra tags, for legacy, malformed and other prefix cases */
	tags?: string[];
	/** default "v" */
	tagPrefix?: string;
	lockfile?: boolean;
	/**
	 * Raw files at paths relative to the repo root, written after every manifest so they can override
	 * one. For the shapes that do not belong to a package at all: compose files, Dockerfiles, and a
	 * .gitignore.
	 */
	files?: Record<string, string>;
};

export type Repo = {
	dir: string;
	git: ReturnType<typeof gitIn>;
	read: (file: string) => Promise<string>;
	/** dirties the working tree, for the cases that only exist uncommitted */
	write: (file: string, text: string) => Promise<unknown>;
	versionOf: (name: string) => Promise<string>;
	tags: () => Promise<string[]>;
	/** the package directories, i.e. the tool's `--paths` list */
	paths: string[];
	cleanup: () => Promise<void>;
};

export const nodePackage = (
	name: string,
	version: string,
	extra?: Partial<PackageSpec>,
): PackageSpec => ({ name, type: "node", version, ...extra });

export const pythonPackage = (
	name: string,
	version: string,
	extra?: Partial<PackageSpec>,
): PackageSpec => ({ name, type: "python", version, ...extra });

export const released = (
	version: string,
	extra?: Partial<ReleaseSpec>,
): ReleaseSpec => ({ version, ...extra });

const dirOf = (pkg: PackageSpec) =>
	pkg.dir ?? (pkg.type === "python" ? pkg.name.replaceAll("-", "_") : pkg.name);

const manifestOf = (pkg: PackageSpec) =>
	`${dirOf(pkg)}/${pkg.type === "python" ? "pyproject.toml" : "package.json"}`;

/** tab indented with `version` last, matching the root and configurator package.json files */
const jsonManifest = (fields: Record<string, unknown>, version: string) =>
	`${JSON.stringify({ ...fields, version }, null, "\t")}\n`;

const specifiers = (deps: PackageSpec["deps"]) =>
	Object.fromEntries(
		Object.entries(deps ?? {}).map(([name, pin]) => [name, pin ?? "*"]),
	);

const nodeManifest = (pkg: PackageSpec) =>
	jsonManifest(
		{
			name: pkg.name,
			private: true,
			dependencies: specifiers(pkg.deps),
			devDependencies: specifiers(pkg.devDeps),
		},
		pkg.version,
	);

const requirements = (deps: PackageSpec["deps"]) =>
	Object.entries(deps ?? {}).map(
		([name, pin]) => `    "${pin ? `${name}==${pin}` : name}",`,
	);

const pythonManifest = (pkg: PackageSpec, dirs: Map<string, string>) => {
	const deps = Object.entries({ ...pkg.deps, ...pkg.devDeps });
	const sources = deps.map(([name]) => {
		const target = dirs.get(name);
		if (!target)
			throw new Error(`fixture ${pkg.name} depends on unknown package ${name}`);
		const relative = path.posix.relative(dirOf(pkg), target);
		return `${name} = { path = "${relative}", editable = true }`;
	});
	const dev = requirements(pkg.devDeps);
	return `${[
		"[project]",
		`name = "${pkg.name}"`,
		`version = "${pkg.version}"`,
		'requires-python = ">=3.12"',
		"dependencies = [",
		...requirements(pkg.deps),
		"]",
		...(dev.length ? ["", "[dependency-groups]", "dev = [", ...dev, "]"] : []),
		...(sources.length ? ["", "[tool.uv.sources]", ...sources] : []),
	].join("\n")}\n`;
};

type State = {
	root: string;
	packages: PackageSpec[];
	files?: Record<string, string>;
};

const stateAt = (spec: RepoSpec, release: ReleaseSpec): State => ({
	root: release.root ?? release.version,
	files: spec.files,
	packages: spec.packages
		.filter((pkg) => !release.absent?.includes(pkg.name))
		.map((pkg) => ({
			...pkg,
			version: release.versions?.[pkg.name] ?? pkg.version,
		})),
});

/**
 * Wipes and rewrites the whole tree, so there is no incremental bookkeeping and `absent` falls out for
 * free in both directions.
 */
const writeTree = async (
	dir: string,
	state: State,
	counters: Map<string, number>,
	dirs: Map<string, string>,
) => {
	for (const entry of await readdir(dir))
		if (entry !== ".git")
			await rm(path.join(dir, entry), { recursive: true, force: true });
	await Bun.write(
		path.join(dir, "package.json"),
		jsonManifest(
			{
				name: "fixture-root",
				private: true,
				workspaces: state.packages
					.filter((pkg) => pkg.type === "node")
					.map((pkg) => `${dirOf(pkg)}/`),
			},
			state.root,
		),
	);
	for (const pkg of state.packages) {
		await Bun.write(
			path.join(dir, manifestOf(pkg)),
			pkg.type === "python" ? pythonManifest(pkg, dirs) : nodeManifest(pkg),
		);
		// a counter rather than an added file: git diff ignores untracked paths
		await Bun.write(
			path.join(dir, dirOf(pkg), "source.txt"),
			`${counters.get(pkg.name) ?? 0}\n`,
		);
		for (const [file, text] of Object.entries(pkg.files ?? {}))
			await Bun.write(path.join(dir, dirOf(pkg), file), text);
	}
	// last, so a raw file can replace a manifest this builder just wrote, the root's included
	for (const [file, text] of Object.entries(state.files ?? {}))
		await Bun.write(path.join(dir, file), text);
};

export const createRepo = async (spec: RepoSpec): Promise<Repo> => {
	const dir = await mkdtemp(path.join(os.tmpdir(), "versioning-"));
	// the builder must fail loudly, so it does not use the lenient git from ../git
	const setup = (...args: string[]) => run(["git", ...args], { cwd: dir });
	await setup("init", "-b", "main");
	for (const [key, value] of [
		["user.name", "Fixture"],
		["user.email", "fixture@example.com"],
		// a developer with global signing turned on would otherwise fail every test
		["commit.gpgsign", "false"],
		["tag.gpgsign", "false"],
		// keep file bytes stable on Windows
		["core.autocrlf", "false"],
	])
		await setup("config", key, value);

	const dirs = new Map(spec.packages.map((pkg) => [pkg.name, dirOf(pkg)]));
	const counters = new Map<string, number>();
	const touch = (names?: string[]) => {
		for (const name of names ?? [])
			counters.set(name, (counters.get(name) ?? 0) + 1);
	};
	const releases = spec.releases ?? [];
	const prefix = spec.tagPrefix ?? "v";
	for (const release of releases) {
		touch(release.touch);
		await writeTree(dir, stateAt(spec, release), counters, dirs);
		await setup("add", "-A");
		await setup("commit", "--allow-empty", "-m", `release ${release.version}`);
		await setup("tag", `${prefix}${release.version}`);
	}
	touch(spec.touch);
	const last = releases.at(-1);
	const root = spec.root ?? last?.root ?? last?.version ?? "0.1.0";
	await writeTree(
		dir,
		{ root, packages: spec.packages, files: spec.files },
		counters,
		dirs,
	);
	await setup("add", "-A");
	await setup("commit", "--allow-empty", "-m", "current");
	for (const tag of spec.tags ?? []) await setup("tag", tag);
	if (spec.lockfile)
		await run(["bun", "install", "--lockfile-only"], { cwd: dir });

	const git = gitIn(dir);
	return {
		dir,
		git,
		read: (file) => Bun.file(path.join(dir, file)).text(),
		write: (file, text) => Bun.write(path.join(dir, file), text),
		/** parsed here rather than with the tool's own reader, so a bug in it cannot hide itself */
		versionOf: async (name) => {
			const pkg = spec.packages.find((candidate) => candidate.name === name);
			if (!pkg) throw new Error(`no fixture package named ${name}`);
			const text = await Bun.file(path.join(dir, manifestOf(pkg))).text();
			if (pkg.type === "node") return JSON.parse(text).version as string;
			const match = /^version\s*=\s*"([^"]+)"/m.exec(text);
			if (!match) throw new Error(`no version in ${manifestOf(pkg)}`);
			return match[1] as string;
		},
		tags: async () => (await git("tag")).stdout.split("\n").filter(Boolean),
		paths: spec.packages.map(dirOf),
		cleanup: async () => {
			if (process.env.KEEP_FIXTURE) {
				console.log(`fixture kept at ${dir}`);
				return;
			}
			// git marks pack files read only, which makes a plain rm flaky on Windows
			await rm(dir, { recursive: true, force: true, maxRetries: 3 });
		},
	};
};

/** registers beforeEach/afterEach and hands back a handle repopulated before each test body */
export const useRepo = (spec: RepoSpec) => {
	const repo = {} as Repo;
	beforeEach(async () => {
		Object.assign(repo, await createRepo(spec));
	});
	// optional call: a build that threw leaves nothing to clean up
	afterEach(() => repo.cleanup?.());
	return repo;
};
