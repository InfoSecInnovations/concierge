import path from "node:path";
import * as dotenv from "dotenv";
import buildProgram from "./buildProgram";

// we set this to 'executable' when building the standalone
const environment = process.env.SHABTI_ENVIRONMENT_TYPE || "local";
// the environment file is in a different location when running in the executable as opposed to the local code
const envPath =
	environment == "executable"
		? ["docker_compose", ".env"]
		: ["..", "shabti_configurator", "docker_compose", ".env"];
dotenv.config({ path: path.resolve(path.join(...envPath)) });

const program = await buildProgram();
await program.parseAsync(Bun.argv);
