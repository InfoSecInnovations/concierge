import * as envfile from "envfile";
import getEnvPath from "./getEnvPath";
import getShabtiRunState, { type ShabtiRunState } from "./shabtiRunState";
import { WebUILink } from "./webUiLink";

export const RelaunchForm = async (props: {
	isLocal: boolean;
	localIsRunning: boolean;
}) => {
	const envs = envfile.parse(await Bun.file(getEnvPath()).text());
	const containers = await getShabtiRunState();
	// the watch process means we launched the local configuration ourselves, but it can also be
	// running from the devcontainer or a test run, in which case we go by the containers
	const ownsWatchProcess = props.isLocal && props.localIsRunning;
	const runState: ShabtiRunState = ownsWatchProcess
		? "running"
		: containers.state;
	// relaunching a local configuration we don't own takes it over
	const canLaunch = props.isLocal ? !ownsWatchProcess : runState != "running";
	const canStop = runState != "stopped";
	return (
		<form action="/launch" method="post">
			<fieldset>
				<legend>Launch</legend>
				{!props.isLocal || runState != "stopped" ? (
					<>
						<WebUILink></WebUILink>
						{canLaunch && (
							<p>
								If the link above isn't working, try (re)launching using the
								button below.
							</p>
						)}
						<p>
							Bear in mind that if you just installed Shabti it can take a few
							minutes before it's up and running.
						</p>
					</>
				) : (
					<>
						<p>
							Use the button below to launch Shabti in development mode with
							reloading.
						</p>
						<p>
							We recommend using Visual Studio Code with the provided
							devcontainer configuration instead of launching Shabti from here.
						</p>
					</>
				)}
				{runState == "partial" && (
					<p class="error">
						Shabti isn't running properly, the following services are down:{" "}
						{containers.stopped.join(", ")}. Relaunch to bring everything back
						up, or stop Shabti if you don't want to use it right now.
					</p>
				)}
				<p>
					<input
						type="checkbox"
						id="launch_with_gpu"
						name="use_gpu"
						checked={envs.SHABTI_COMPUTE == "cuda"}
					></input>
					<label for="launch_with_gpu">Enable GPU Acceleration</label>
				</p>
				{canLaunch && (
					<button type="submit">
						{canStop ? "Relaunch Shabti" : "Launch Shabti"}
					</button>
				)}
				{canStop && (
					<button type="submit" name="environment" value="stop">
						Stop Shabti
					</button>
				)}
			</fieldset>
		</form>
	);
};
