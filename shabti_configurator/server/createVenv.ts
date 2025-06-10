import path from "node:path";
import util from "node:util";
import runPython from "./runPython";
const exec = util.promisify(
	await import("node:child_process").then(
		(child_process) => child_process.exec,
	),
);

export default async (pathSegments: string[] = []) => {
	// some systems only have python3 as the executable and others only have python, just in case someone has a whole other configuration we'll log an error but continue installing
	await exec("python3 -m venv .", {
		cwd: path.resolve(path.join("..", ...pathSegments)),
	})
		.catch(() =>
			exec("python -m venv .", {
				cwd: path.resolve(path.join("..", ...pathSegments)),
			}),
		)
		.then(
			() => runPython("pip install -r dev_requirements.txt", pathSegments),
			() =>
				console.error(`Python virtual environment was unable to be configured in ${path.resolve(path.join("..", ...pathSegments))}! 
Please follow the instructions appropriate to your operating system and Python configuration to do so manually.
Once the environment is configured you will need to install the dependencies from the dev_requirements.txt in this directory.
`),
		);
};
