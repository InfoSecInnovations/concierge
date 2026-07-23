import packageJson from "./package.json";
import apiProject from "./docker_containers/shabti_api/pyproject.toml";
import webProject from "./docker_containers/shabti_web/pyproject.toml";
import configuratorVersions from "./configurator-versions.json";

const componentsFile = Bun.file("./shabti-components.json");
await Bun.write(
	componentsFile,
	JSON.stringify(
		{
			...configuratorVersions,
			version: packageJson.version,
			apiVersion: apiProject.project.version,
			webVersion: webProject.project.version,
		},
		null,
		"\t",
	),
);
