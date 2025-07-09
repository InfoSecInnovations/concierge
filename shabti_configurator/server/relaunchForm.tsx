import * as envfile from "envfile";
import getEnvPath from "./getEnvPath";

export const RelaunchForm = async (props: {
	devMode: boolean;
	apiIsRunning?: boolean;
	webIsRunning?: boolean;
}) => {
	const envs = envfile.parse(await Bun.file(getEnvPath()).text());
	return (
		<form action="/launch" method="post">
			<p>
				<input
					type="checkbox"
					id="launch_with_gpu"
					name="use_gpu"
					checked={envs.SHABTI_COMPUTE == "cuda"}
				></input>
				<label for="launch_with_gpu">Enable GPU Acceleration</label>
			</p>
			<button type="submit">Launch Shabti</button>
			{props.devMode && (
				<>
					<button type="submit" name="environment" value="local">
						Launch API Locally (Docker)
					</button>
					{props.apiIsRunning ? (
						<button type="submit" name="environment" value="stop_development">
							Stop API (Python)
						</button>
					) : (
						<button type="submit" name="environment" value="development">
							Launch API Locally (Python)
						</button>
					)}
					<button type="submit" name="environment" value="web_local">
						Launch Web UI Locally (Docker)
					</button>
					{props.webIsRunning ? (
						<button
							type="submit"
							name="environment"
							value="stop_web_development"
						>
							Stop Web UI (Python)
						</button>
					) : (
						<button type="submit" name="environment" value="web_development">
							Launch Web UI Locally (Python)
						</button>
					)}
				</>
			)}
		</form>
	);
};
