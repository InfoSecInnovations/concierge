import path from "node:path";
import getDefaultModelSelection from "../shabti_configurator/getDefaultModelSelection";
import writeModelsIni from "../shabti_configurator/server/writeModelsIni";

// the compose files here pull in the llama.cpp service from the configurator, which bind mounts
// my-models.ini. That file is generated during a normal install, but the tests never run one,
// so we have to write it ourselves or Docker will mount an empty directory in its place.
export default () =>
	getDefaultModelSelection().then((selection) =>
		writeModelsIni(
			selection,
			path.join(import.meta.dir, "..", "shabti_configurator"),
		),
	);
