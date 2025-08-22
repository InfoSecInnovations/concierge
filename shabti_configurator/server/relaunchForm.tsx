import * as envfile from "envfile";
import getEnvPath from "./getEnvPath";

export const RelaunchForm = async (props: {
	devMode: boolean;
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
						Launch Docker Configuration for Local Development
					</button>
				</>
			)}
		</form>
	);
};
