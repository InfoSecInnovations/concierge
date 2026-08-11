/**
 * Every version number we own, where it is declared, everywhere it is referenced, and how to tell
 * whether the component behind it has actually changed.
 *
 * Adding a new pin to a file is only safe if it is added here too: the writers assert that the value
 * they are replacing matches the component's declared version, so a pin that nothing knows about
 * will drift silently while an unregistered one that does get written to will fail loudly.
 *
 * Deliberately absent: the root pyproject.toml. Its version is the dev only uv workspace root, which
 * is never published and never referenced.
 */

export type Scope = "shabti" | "launcher";

export type VersionRef =
	// the first `version = "..."` line of a pyproject.toml, i.e. the one in [project]
	| { kind: "pyprojectVersion"; file: string }
	// the top level `"version": "..."` of a package.json
	| { kind: "packageJsonVersion"; file: string }
	// a `<pkg>==<version>` line of a requirements.txt
	| { kind: "requirementsPin"; file: string; pkg: string }
	// a `"<pkg>==<version>"` entry in any dependency array of a pyproject.toml
	| { kind: "pyprojectDepPin"; file: string; pkg: string }
	// the version of a uv.lock's own [[package]] entry
	| { kind: "uvLockSelf"; file: string; pkg: string };

export type ChangeProbe =
	// compare a freshly built sdist against the one published on PyPI
	| { kind: "pypiSdist" }
	// compare these paths against the baseline release tag
	| { kind: "git"; paths: string[] }
	// no comparison: this version moves on every release
	| { kind: "always" };

export type ComponentRegistry =
	| { kind: "pypi"; name: string }
	| { kind: "npm"; name: string }
	| { kind: "docker"; repo: string }
	| { kind: "githubRelease" }
	| { kind: "none" };

export interface Component {
	id: string;
	label: string;
	dir: string;
	scopes: Scope[];
	registry: ComponentRegistry;
	/** where the version is read from */
	source: VersionRef;
	/** every place the version is written to, including the source */
	refs: VersionRef[];
	probe: ChangeProbe;
	/** dependencies that leave no version reference behind, so cannot be derived */
	extraDependsOn?: string[];
}

const pythonPackage = (
	id: string,
	dir: string,
	pypiName: string,
	pinnedIn: VersionRef[],
): Component => ({
	id,
	label: pypiName,
	dir,
	scopes: ["shabti"],
	registry: { kind: "pypi", name: pypiName },
	source: { kind: "pyprojectVersion", file: `${dir}/pyproject.toml` },
	refs: [
		{ kind: "pyprojectVersion", file: `${dir}/pyproject.toml` },
		...pinnedIn,
	],
	probe: { kind: "pypiSdist" },
});

const API_DIR = "docker_containers/shabti_api";
const WEB_DIR = "docker_containers/shabti_web";
const API_CLIENT_DIR = "python_packages/shabti_api_client";

const apiPin = (pkg: string): VersionRef => ({
	kind: "requirementsPin",
	file: `${API_DIR}/requirements.txt`,
	pkg,
});
const webPin = (pkg: string): VersionRef => ({
	kind: "requirementsPin",
	file: `${WEB_DIR}/requirements.txt`,
	pkg,
});
const apiClientPin = (pkg: string): VersionRef => ({
	kind: "pyprojectDepPin",
	file: `${API_CLIENT_DIR}/pyproject.toml`,
	pkg,
});

const container = (
	id: string,
	dir: string,
	pyPiName: string,
	dockerRepo: string,
): Component => ({
	id,
	label: dockerRepo,
	dir,
	scopes: ["shabti"],
	registry: { kind: "docker", repo: dockerRepo },
	source: { kind: "pyprojectVersion", file: `${dir}/pyproject.toml` },
	refs: [
		{ kind: "pyprojectVersion", file: `${dir}/pyproject.toml` },
		{ kind: "uvLockSelf", file: `${dir}/uv.lock`, pkg: pyPiName },
	],
	probe: { kind: "git", paths: [dir] },
});

// ordered dependencies first, which also makes the topological sort stable
export const COMPONENTS: Component[] = [
	pythonPackage("shabtiTypes", "python_packages/shabti_types", "shabti-types", [
		apiPin("shabti-types"),
		webPin("shabti-types"),
		apiClientPin("shabti-types"),
	]),
	pythonPackage("shabtiUtil", "python_packages/shabti_util", "shabti-util", [
		apiPin("shabti-util"),
		webPin("shabti-util"),
	]),
	pythonPackage("isiUtil", "python_packages/isi_util", "isi-util", [
		apiPin("isi-util"),
	]),
	pythonPackage(
		"shabtiKeycloak",
		"python_packages/shabti_keycloak",
		"shabti-keycloak",
		[
			apiPin("shabti-keycloak"),
			webPin("shabti-keycloak"),
			apiClientPin("shabti-keycloak"),
		],
	),
	pythonPackage("shabtiApiClient", API_CLIENT_DIR, "shabti-api-client", [
		webPin("shabti-api-client"),
	]),
	container("shabtiApi", API_DIR, "shabti-api", "infosecinnovations/shabti"),
	container(
		"shabtiWeb",
		WEB_DIR,
		"shabti-web",
		"infosecinnovations/shabti-web",
	),
	{
		id: "shabtiApiClientNode",
		label: "@infosecinnovations/shabti-api-client",
		dir: "shabti_api_client_node",
		scopes: ["shabti"],
		registry: { kind: "npm", name: "@infosecinnovations/shabti-api-client" },
		source: {
			kind: "packageJsonVersion",
			file: "shabti_api_client_node/package.json",
		},
		refs: [
			{
				kind: "packageJsonVersion",
				file: "shabti_api_client_node/package.json",
			},
		],
		probe: { kind: "git", paths: ["shabti_api_client_node"] },
	},
	{
		id: "shabtiCli",
		label: "Shabti CLI",
		dir: "shabti_cli",
		scopes: ["shabti"],
		// distributed as an executable in the release zips, so there is no registry to check
		registry: { kind: "none" },
		source: { kind: "packageJsonVersion", file: "shabti_cli/package.json" },
		refs: [{ kind: "packageJsonVersion", file: "shabti_cli/package.json" }],
		probe: { kind: "git", paths: ["shabti_cli"] },
		// depended on via workspace:*, which leaves no version to rewrite
		extraDependsOn: ["shabtiApiClientNode"],
	},
	{
		id: "configurator",
		label: "Shabti Configurator",
		dir: "shabti_configurator",
		// follows its own versioning scheme and is only built and signed by the launcher workflow
		scopes: ["launcher"],
		registry: { kind: "none" },
		source: {
			kind: "packageJsonVersion",
			file: "shabti_configurator/package.json",
		},
		refs: [
			{ kind: "packageJsonVersion", file: "shabti_configurator/package.json" },
		],
		probe: { kind: "git", paths: ["shabti_configurator"] },
	},
	{
		id: "root",
		label: "Shabti",
		dir: ".",
		scopes: ["shabti", "launcher"],
		registry: { kind: "githubRelease" },
		source: { kind: "packageJsonVersion", file: "package.json" },
		refs: [{ kind: "packageJsonVersion", file: "package.json" }],
		probe: { kind: "always" },
	},
];

export const releaseTag = (version: string) => `shabti-v${version}`;

// the workflows use the script's output rather than building this themselves, but it also has to be
// recognisable after the fact so an interrupted release can be resumed instead of bumped again
export const releaseCommitMessage = (version: string) =>
	`increment versions for ${releaseTag(version)}`;

export const inScope = (scope: Scope) =>
	COMPONENTS.filter((component) => component.scopes.includes(scope));

const isUnder = (file: string, dir: string) =>
	dir === "." || file === dir || file.startsWith(`${dir}/`);

/**
 * Which components each component depends on. Derived from the references themselves: if a component
 * pins its version inside another component's directory, that other component depends on it. The
 * root directory contains everything, so the overall Shabti version depends on all of them.
 */
export const dependencyGraph = (components: Component[]) => {
	const graph = new Map<string, string[]>();
	for (const component of components) {
		const dependencies = components
			.filter(
				(other) =>
					other.id !== component.id &&
					other.refs.some((ref) => isUnder(ref.file, component.dir)),
			)
			.map((other) => other.id);
		for (const id of component.extraDependsOn ?? []) {
			if (
				components.some((other) => other.id === id) &&
				!dependencies.includes(id)
			)
				dependencies.push(id);
		}
		graph.set(component.id, dependencies);
	}
	return graph;
};

/** dependencies before dependents, ties broken by declaration order */
export const topoSort = (components: Component[]) => {
	const graph = dependencyGraph(components);
	const sorted: Component[] = [];
	const done = new Set<string>();
	while (sorted.length < components.length) {
		const ready = components.find(
			(component) =>
				!done.has(component.id) &&
				(graph.get(component.id) ?? []).every((id) => done.has(id)),
		);
		if (!ready) {
			const remaining = components
				.filter((component) => !done.has(component.id))
				.map((component) => component.id);
			throw new Error(
				`dependency cycle between components: ${remaining.join(", ")}`,
			);
		}
		sorted.push(ready);
		done.add(ready.id);
	}
	return { sorted, graph };
};
