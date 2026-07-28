import { platform } from "node:os";
import { $ } from "bun";

export default () => {
	if (platform() == "win32") return $`Scripts\\playwright install`.cwd("..");
	return $`./bin/playwright install`.cwd("..");
};
