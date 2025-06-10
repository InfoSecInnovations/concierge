import { platform } from "node:os";
import path from "node:path";
import { $ } from "bun";

export default (command: string, pathSegments: string[] = []) => {
	try {
		if (platform() == "win32")
			return $`Scripts\\python -m ${{ raw: command }}`.cwd(
				path.resolve(path.join("..", ...pathSegments)),
			);
		return $`./bin/python -m ${{ raw: command }}`.cwd(
			path.resolve(path.join("..", ...pathSegments)),
		);
	} catch {
		console.error(`Unable to run command "${command}" in directory ${path.resolve(path.join("..", ...pathSegments))}.
This could happen if the virtual environment was unable to be configured properly, please ensure the virtual environment is created in this directory and try to run the command manually.
`);
	}
};
