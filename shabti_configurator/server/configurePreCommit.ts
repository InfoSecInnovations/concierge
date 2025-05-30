import { platform } from "node:os";
import { $ } from "bun";

export default () => {
	if (platform() == "win32") return $`Scripts\\pre-commit install`.cwd("..");
	return $`./bin/pre-commit install`.cwd("..");
};
