import path from "node:path";
import { rm, stat } from "node:fs/promises";
import * as ini from "@std/ini";
import { HTTPException } from "hono/http-exception";
import _ from "lodash";
import getModelsConfig from "../getModelsConfig";
import type { ModelSelection } from "../getDefaultModelSelection";

// the compiled installer unzips docker_compose next to the working directory,
// so this stays relative to the cwd by default like getEnvPath does
export const getModelsIniPath = (baseDir = path.resolve()) =>
	path.join(
		baseDir,
		"docker_compose",
		"docker_compose_dependencies",
		"llama_models",
		"my-models.ini",
	);

// writes the ini file used by llama.cpp's --models-preset
export default async (selection: ModelSelection, baseDir = path.resolve()) => {
	const { chatModels, embeddingsModel, defaultModel } = selection;
	const shabtiModels = await getModelsConfig();
	const sections = [...chatModels, embeddingsModel].reduce((acc, key) => {
		const modelData = _.cloneDeep(shabtiModels[key]);
		if (!modelData)
			throw new HTTPException(404, { message: `model ${key} not found` });
		const tags = modelData.tags.filter((tag: string) => tag != "default"); // remove the default tag set in the config file
		if (key == defaultModel) {
			// set the default tag if this model is the selected default
			tags.push("default");
		}
		modelData.tags = tags.join(", "); // llama.cpp expects the tags in CSV
		return { ...acc, [key]: modelData };
	}, {});
	const modelsIniPath = getModelsIniPath(baseDir);
	// if a previous run launched the containers before this file existed, Docker will have
	// created a directory here for the bind mount, which would make the write fail
	if (
		await stat(modelsIniPath).then(
			(s) => s.isDirectory(),
			() => false,
		)
	)
		await rm(modelsIniPath, { recursive: true, force: true });
	await Bun.write(modelsIniPath, ini.stringify(sections, { pretty: true }));
	return modelsIniPath;
};
