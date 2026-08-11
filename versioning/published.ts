import { Octokit } from "octokit";
import type { Component } from "./registry";
import { releaseTag } from "./registry";
import { git } from "./repo";
import { toPep440 } from "./versions";

interface PyPiFile {
	packagetype: string;
	url: string;
	yanked?: boolean;
}

interface PyPiProject {
	releases: Record<string, PyPiFile[] | undefined>;
}

const pypiProjects = new Map<string, Promise<PyPiProject | undefined>>();

/** the PyPI metadata for a package, or undefined if it has never been published. Fetched once. */
export const pypiProject = (name: string) => {
	const cached = pypiProjects.get(name);
	if (cached) return cached;
	const project = fetch(`https://pypi.org/pypi/${name}/json`).then(
		async (res) => {
			if (res.status === 404) return undefined;
			if (!res.ok) throw new Error(`PyPI returned ${res.status} for ${name}`);
			return (await res.json()) as PyPiProject;
		},
	);
	pypiProjects.set(name, project);
	return project;
};

export const pypiFiles = async (name: string, version: string) => {
	const project = await pypiProject(name);
	// PyPI stores the PEP 440 normalisation of our semver versions: 0.9.0-alpha.1 is 0.9.0a1
	return project?.releases[toPep440(version)];
};

export const pypiSdist = async (name: string, version: string) =>
	(await pypiFiles(name, version))?.find(
		(file) => file.packagetype === "sdist",
	);

const npmPackages = new Map<string, Promise<Record<string, unknown>>>();

const npmVersions = (name: string) => {
	const cached = npmPackages.get(name);
	if (cached) return cached;
	const versions = fetch(`https://registry.npmjs.org/${name}`).then(
		async (res) => {
			if (res.status === 404) return {};
			if (!res.ok) throw new Error(`npm returned ${res.status} for ${name}`);
			const json = (await res.json()) as { versions?: Record<string, unknown> };
			return json.versions ?? {};
		},
	);
	npmPackages.set(name, versions);
	return versions;
};

const dockerTagExists = async (repo: string, tag: string) => {
	const res = await fetch(
		`https://hub.docker.com/v2/repositories/${repo}/tags/${encodeURIComponent(tag)}/`,
	);
	if (res.status === 404) return false;
	if (!res.ok) throw new Error(`Docker Hub returned ${res.status} for ${repo}`);
	return true;
};

const [owner, repo] = (
	process.env.GITHUB_REPOSITORY || "InfoSecInnovations/shabti"
).split("/");

const releaseExists = async (version: string) => {
	const tag = releaseTag(version);
	const local = await git(
		"rev-parse",
		"--verify",
		"--quiet",
		`refs/tags/${tag}`,
	);
	if (local.exitCode === 0) return true;
	// a release whose tag we don't have locally, or whose tag was deleted, still blocks the name
	const octokit = new Octokit({ auth: process.env.GITHUB_TOKEN });
	const release = await octokit.rest.repos
		.getReleaseByTag({ owner, repo, tag })
		.catch((err: { status?: number }) => {
			if (err.status === 404) return undefined;
			throw err;
		});
	return !!release;
};

export interface PublishedCheck {
	published: boolean;
	/** set when we could not reach the registry, in which case `published` is false */
	warning?: string;
}

/**
 * Whether a version number is already taken. Publishing over an existing number would either be
 * rejected (PyPI, npm) or, worse, silently accepted: pushing an existing Docker tag changes what
 * already installed users pull on their next `docker compose pull`.
 */
export const isPublished = async (
	component: Component,
	version: string,
	options?: { checkDocker?: boolean },
): Promise<PublishedCheck> => {
	try {
		switch (component.registry.kind) {
			case "pypi":
				return {
					published: !!(await pypiFiles(component.registry.name, version)),
				};
			case "npm":
				return {
					published: version in (await npmVersions(component.registry.name)),
				};
			case "docker":
				if (options?.checkDocker === false) return { published: false };
				return {
					published: await dockerTagExists(component.registry.repo, version),
				};
			case "githubRelease":
				return { published: await releaseExists(version) };
			case "none":
				return { published: false };
		}
	} catch (err) {
		return {
			published: false,
			warning: `could not check whether ${component.label} ${version} is already published: ${err instanceof Error ? err.message : err}`,
		};
	}
};
