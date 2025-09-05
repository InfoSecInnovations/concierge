import path from "node:path";
import { $ } from "bun";
import shabtiApiPackageJson from "./shabti_api_client_node/package.json";
import shabtiApiPyProject from "./python_packages/shabti_api_client/pyproject.toml";
import shabtiKeycloakPyProject from "./python_packages/shabti_keycloak/pyproject.toml";
import shabtiTypesPyProject from "./python_packages/shabti_types/pyproject.toml";
import shabtiUtilPyProject from "./python_packages/shabti_util/pyproject.toml";
import isiUtilPyProject from "./python_packages/isi_util/pyproject.toml";
import packageJson from "./package.json";
import AdmZip from "adm-zip";
import * as readline from "readline-sync";

console.log("Shabti release publisher\n");
console.log(`Current version: ${packageJson.version}`);
let version: string | null = null;
while (!version) {
	version = prompt("Input new Shabti version:");
}
packageJson.version = version;
await Bun.write("./package.json", JSON.stringify(packageJson, undefined, "\t"));
let pyPiKey: string | null = null;
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
	} catch {} // if the above block fails it probably means the package doesn't exist
	while (!pyPiKey) {
		pyPiKey = readline.question("Please provide your PyPI API key: ", {
			hideEchoBack: true,
			mask: "",
		});
	}
	console.log("\n");
	const packageDir = path.resolve(
		path.join(import.meta.dir, "python_packages", packageName),
	);
	await $`rm -rf ${path.join(packageDir, "dist")}`;
	await $`uv build`.cwd(packageDir);
	await $`uv publish --token ${pyPiKey}`.cwd(packageDir);
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
await $`docker build --target cpu -t infosecinnovations/shabti:${version} ./docker_containers/shabti_api`;
await $`docker image push infosecinnovations/shabti:${version}`;
await $`docker build --target cuda -t infosecinnovations/shabti:${version}-cuda ./docker_containers/shabti_api`;
await $`docker image push infosecinnovations/shabti:${version}-cuda`;
await $`docker build -t infosecinnovations/shabti-web:${version} ./docker_containers/shabti_web`;
await $`docker image push infosecinnovations/shabti-web:${version}`;
await $`git add -A`;
await $`git commit -m 'increment version to ${version}'`;
await $`git push`;
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
const distDir = path.resolve(path.join(import.meta.dir, "dist"));
const winZip = new AdmZip();
winZip.addLocalFile(
	path.join(configuratorDir, "dist", "windows", "shabti.exe"),
);
winZip.addLocalFile(path.join(cliDir, "dist", "windows", "shabti_cli.exe"));
winZip.writeZip(path.resolve(path.join(distDir, "shabti_win.zip")));
const linuxZip = new AdmZip();
linuxZip.addLocalFile(path.join(configuratorDir, "dist", "linux", "shabti"));
linuxZip.addLocalFile(path.join(cliDir, "dist", "linux", "shabti_cli"));
linuxZip.writeZip(path.resolve(path.join(distDir, "shabti_linux.zip")));
const macZip = new AdmZip();
macZip.addLocalFile(path.join(configuratorDir, "dist", "mac", "shabti"));
macZip.addLocalFile(path.join(cliDir, "dist", "mac", "shabti_cli"));
macZip.writeZip(path.resolve(path.join(distDir, "shabti_mac.zip")));
const gitBranch = await $`git branch --show-current`
	.text()
	.then((branch) => branch.trim());
await $`gh release create ${version} ./dist/*.zip --target ${gitBranch}`;
