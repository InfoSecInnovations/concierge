import * as envfile from "envfile";
import getEnvPath from "./getEnvPath";

// reads the environment file, or an empty configuration when Shabti hasn't been installed yet,
// so the forms which are rendered in both cases don't each have to guard for it
export default async (): Promise<ReturnType<typeof envfile.parse>> => {
	const envFile = Bun.file(getEnvPath());
	if (!(await envFile.exists())) return {};
	return envfile.parse(await envFile.text());
};
