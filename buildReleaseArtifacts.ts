/*
Required environment variables:
UV_PUBLISH_TOKEN - PyPI API key with permissions to publish the Shabti related packages
NPM_CONFIG_TOKEN - NPM token for automated workflows (doesn't appear in the script but will be used by bun publish)
DOCKER_USERNAME - Docker Hub username
DOCKER_PASSWORD - Docker Hub password
*/

import path from "node:path";
import util from "node:util";
import { $ } from "bun";
import shabtiApiPackageJson from "./shabti_api_client_node/package.json";
import shabtiApiPyProject from "./python_packages/shabti_api_client/pyproject.toml";
import shabtiKeycloakPyProject from "./python_packages/shabti_keycloak/pyproject.toml";
import shabtiTypesPyProject from "./python_packages/shabti_types/pyproject.toml";
import shabtiUtilPyProject from "./python_packages/shabti_util/pyproject.toml";
import isiUtilPyProject from "./python_packages/isi_util/pyproject.toml";
import packageJson from "./package.json";
import { platform } from "node:os";
const exec = util.promisify(
	await import("node:child_process").then(
		(child_process) => child_process.exec,
	),
);

const runPython = (command: string, directoryPath: string[] = []) => {
	if (platform() == "win32")
		return $`Scripts\\python -m ${{ raw: command }}`.cwd(
			path.resolve(path.join(...directoryPath)),
		);
	return $`./bin/python -m ${{ raw: command }}`.cwd(
		path.resolve(path.join(...directoryPath)),
	);
};

Bun.env.TWINE_USER = "__token__"; // this username tells twine we'll be using a token to interact with PyPI
const version = packageJson.version;
console.log(`Publishing release for Shabti ${version}`);
packageJson.version = version;
const handlePyPi = async (
	packageUrlName: string,
	packageName: string,
	tomlData: any,
) => {
	try {
		const pyPiJson: any = await fetch(
			`https://pypi.org/pypi/${packageUrlName}/json`,
		).then((res) => res.json());
		if (pyPiJson.releases[tomlData.project.version]) {
			console.log(`Python package ${packageName} already up to date`);
			return;
		}
	} catch {
		console.log(`PyPI package ${packageUrlName} not found on PyPI`);
	} // if the above block fails it probably means the package doesn't exist
	const packageDir = path.resolve(
		path.join(import.meta.dir, "python_packages", packageName),
	);
	await $`rm -rf ${path.join(packageDir, "dist")}`;
	await $`uv build`.cwd(packageDir);
	await $`uv publish`.cwd(packageDir);
};
await handlePyPi("shabti-util", "shabti_util", shabtiUtilPyProject);
await handlePyPi("isi-util", "isi_util", isiUtilPyProject);
await handlePyPi("shabti-api-client", "shabti_api_client", shabtiApiPyProject);
await handlePyPi("shabti-keycloak", "shabti_keycloak", shabtiKeycloakPyProject);
await handlePyPi("shabti-types", "shabti_types", shabtiTypesPyProject);
const npmJson: any = await fetch(
	"https://registry.npmjs.org/@infosecinnovations/shabti-api-client",
).then((res) => res.json());
const nodeClientDir = path.resolve(
	path.join(import.meta.dir, "shabti_api_client_node"),
);
await $`bun run build`.cwd(nodeClientDir);
if (npmJson.versions[shabtiApiPackageJson.version]) {
	console.log("Shabti API Node Client already up to date");
} else {
	await $`bun publish --access public`.cwd(nodeClientDir); // TODO: detect if prerelease
}
await $`echo "$DOCKER_PASSWORD" | docker login -u "$DOCKER_USERNAME" --password-stdin`;
await $`docker build --target cpu -t infosecinnovations/shabti:${version} ./docker_containers/shabti_api`;
await $`docker image push infosecinnovations/shabti:${version}`;
await $`docker build --target cuda -t infosecinnovations/shabti:${version}-cuda ./docker_containers/shabti_api`;
await $`docker image push infosecinnovations/shabti:${version}-cuda`;
await $`docker build -t infosecinnovations/shabti-web:${version} ./docker_containers/shabti_web`;
await $`docker image push infosecinnovations/shabti-web:${version}`;
const configuratorDir = path.resolve(
	path.join(import.meta.dir, "shabti_configurator"),
);
await $`rm -rf ./dist`.cwd(configuratorDir); // clean dist directory in case we've been running stuff from there
await $`bun run build_win`.cwd(configuratorDir);
await $`bun run build_linux`.cwd(configuratorDir);
await $`bun run build_mac`.cwd(configuratorDir);
const cliDir = path.resolve(path.join(import.meta.dir, "shabti_cli"));
await $`rm -rf ./dist`.cwd(cliDir); // clean dist directory in case we've been running stuff from there
await $`bun run build_win`.cwd(cliDir);
await $`bun run build_linux`.cwd(cliDir);
await $`bun run build_mac`.cwd(cliDir);
