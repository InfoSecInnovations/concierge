import path from "node:path";
import * as envfile from "envfile";
import { keycloakExists } from "./dockerItemsExist";
import getDefaultDirectory from "./getDefaultDirectory";
import getEnvPath from "./getEnvPath";

export const InstallOptionsForm = async (props: { devMode: boolean }) => {
	const envFile = Bun.file(getEnvPath());
	const envs =
		(await envFile.exists()) &&
		(await envFile.text().then((body) => envfile.parse(body)));
	const securityEnabled = envs && envs.SHABTI_SECURITY_ENABLED == "True";
	const demoEnabled = securityEnabled && envs.IS_SECURITY_DEMO == "True";
	const gpuEnabled = envs && envs.SHABTI_COMPUTE == "cuda";
	const loggingEnabled = envs && envs.SHABTI_BASE_SERVICE?.endsWith("logging");
	const logDir =
		(envs && envs.SHABTI_LOG_DIR) ||
		path.join(getDefaultDirectory()!, "shabti", "logs");
	const keycloakEnabled = await keycloakExists();
	return (
		<form action="/install" method="post" id="install_form">
			<fieldset>
				<legend>LLM Configuration</legend>
				<p>
					<input
						type="checkbox"
						id="use_gpu"
						name="use_gpu"
						checked={gpuEnabled}
					></input>
					<label for="use_gpu">Enable GPU Acceleration</label>
				</p>
				<p>
					<label for="language_model">Select Language Model</label>
					<select name="language_model" id="language_model">
						<option value="mistral">mistral</option>
					</select>
					Note that this option doesn't do anything yet, for now the model is
					hardcoded to mistral.
				</p>
			</fieldset>
			<fieldset>
				<legend>Logging</legend>
				<p>
					<input
						type="checkbox"
						id="activity_logging"
						name="activity_logging"
						checked={loggingEnabled}
					></input>
					<label for="activity_logging">Enable Activity Logging</label>
				</p>
				<p class="logging_element">
					<label for="logging_location">Log Directory</label>
					<input
						type="text"
						name="logging_location"
						id="logging_location"
						value={logDir}
					></input>
				</p>
			</fieldset>
			<fieldset>
				<legend>Hosts and Ports</legend>
				<p>
					<label for="web-host">Web Host</label>
					<input
						type="text"
						name="web-host"
						id="web-host"
						value="localhost"
					></input>
					This should be the URL from which the Shabti Web UI is being accessed.
					Leave it as "localhost" unless you need to access Shabti from another
					machine.
				</p>
				<p>
					<label for="web-port">Web Port</label>
					<input
						type="number"
						name="web-port"
						id="web-port"
						value="15130"
					></input>
					The Shabti Web UI will be served on this port.
				</p>
				<p>
					<label for="host">API Host</label>
					<input
						type="text"
						name="api-host"
						id="host"
						value="localhost"
					></input>
					This should be the URL from which the Shabti API is being accessed.
					Leave it as "localhost" unless you need to access Shabti from another
					machine.
				</p>
				<p>
					<label for="port">API Port</label>
					<input type="number" name="api-port" id="port" value="15131"></input>
					The Shabti API will be served on this port.
				</p>
			</fieldset>
			<fieldset>
				<legend>Security Level</legend>
				<p>
					<input
						type="radio"
						value="none"
						id="security_none"
						name="security_level"
						checked={!securityEnabled}
					></input>
					<label for="security_none">None</label>
				</p>
				<p>
					<input
						type="radio"
						value="demo"
						id="security_demo"
						name="security_level"
						checked={demoEnabled}
					></input>
					<label for="security_demo">Demo</label>
				</p>
				<p>
					<input
						type="radio"
						value="enabled"
						id="security_enabled"
						name="security_level"
						checked={securityEnabled && !demoEnabled}
					></input>
					<label for="security_enabled">Enabled</label>
				</p>
				<p>
					If you don't enable security anyone who can access the web UI will
					have full privileges to interact with your Shabti instance!
				</p>
				<p>
					The demo configuration should never be used for production as it is a
					very insecure configuration designed to show off the different access
					levels using test users.
				</p>
				{keycloakEnabled ? (
					<div id="keycloak_config">
						<p>
							<strong>There is an existing Keycloak installation.</strong>
						</p>
						<p>
							We strongly recommend removing that and OpenSearch using the
							buttons above before proceeding.
						</p>
						<p>
							If not the installer will attempt to keep the existing
							configuration but be aware that this isn't well supported and you
							may end up with an unusable setup.
						</p>
					</div>
				) : (
					<p id="keycloak_config">
						<label for="keycloak_password_first">Keycloak Admin Password</label>
						<input type="password" id="keycloak_password_first"></input>
						<label for="keycloak_password">
							Confirm Keycloak Admin Password
						</label>
						<input
							type="password"
							id="keycloak_password"
							name="keycloak_password"
						></input>
					</p>
				)}
				<div id="password_status" class="error"></div>
			</fieldset>
			<button type="submit" id="install_submit" class="install_button">
				Start Installation!
			</button>
			{props.devMode && (
				<button
					type="submit"
					id="install_submit_dev"
					class="install_button"
					name="dev_mode"
					value="True"
				>
					Install Development Configuration
				</button>
			)}
		</form>
	);
};
