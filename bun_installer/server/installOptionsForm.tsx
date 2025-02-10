import path from "node:path"
import getDefaultDirectory from "./getDefaultDirectory"
import * as envfile from "envfile"
import getEnvPath from "./getEnvPath"

export const InstallOptionsForm = async () => {
    const envFile = Bun.file(getEnvPath())
    const envs = await envFile.exists() && await envFile.text().then(body => envfile.parse(body))
    const securityEnabled = envs && envs.CONCIERGE_SECURITY_ENABLED == "True"
    const demoEnabled = securityEnabled && envs.IS_SECURITY_DEMO == "True"
    const gpuEnabled = envs && envs.OLLAMA_SERVICE == "ollama-gpu"
    return (
        <form action="/install" method="post" id="install_form">
            <fieldset>
                <legend>LLM Configuration</legend>
                <p>
                    <input type="checkbox" id="use_gpu" name="use_gpu" checked={gpuEnabled}></input>
                    <label for="use_gpu">Enable GPU Acceleration</label>
                </p>
                <p>
                    <label for="language_model">Select Language Model</label>
                    <select name="language_model" id="language_model">
                        <option value="mistral">mistral</option>
                    </select>
                    Note that this option doesn't do anything yet, for now the model is hardcoded to mistral.
                </p>
            </fieldset>
            <fieldset>
                <legend>Logging</legend>
                <p>
                    <input type="checkbox" id="activity_logging" name="activity_logging"></input>
                    <label for="activity_logging">Enable Activity Logging</label>
                </p>
                <p class="logging_element">
                    <label for="logging_directory">Logging Directory</label>
                    <input type="text" name="logging_directory" id="logging_directory" value={path.join(getDefaultDirectory()!, "logs")}></input>
                </p>
                <p class="logging_element">
                    <label for="logging_retention">Logging Retention</label>
                    <input type="number" name="logging_retention" id="logging_retention" value="90"></input>
                    days
                </p>
            </fieldset>
            <fieldset>
                <legend>Web UI Access</legend>
                <p>
                    <label for="host">Host</label>
                    <input type="text" name="host" id="host" value="localhost"></input>
                    This should be the URL from which Concierge is being accessed. Leave it as "localhost" unless you need to access Concierge from another machine.
                </p>
                <p>
                    <label for="port">Port</label>
                    <input type="number" name="port" id="port" value="15130"></input>
                    Concierge will be served on this port.
                </p>
            </fieldset>
            <fieldset>
                <legend>Security Level</legend>
                <p>
                    <input type="radio" value="none" id="security_none" name="security_level" checked={!securityEnabled}></input>
                    <label for="security_none">None</label>
                </p>
                <p>
                    <input type="radio" value="demo" id="security_demo" name="security_level" checked={demoEnabled}></input>
                    <label for="security_demo">Demo</label>
                </p>
                <p>
                    <input type="radio" value="enabled" id="security_enabled" name="security_level" checked={securityEnabled && !demoEnabled}></input>
                    <label for="security_enabled">Enabled</label>
                </p>
                <p>If you don't enable security anyone who can access the web UI will have full privileges to interact with your Concierge instance!</p>
                <p>The demo configuration should never be used for production as it is a very insecure configuration designed to show off the different access levels using test users.</p>
                <p id="keycloak_config">
                    <label for="keycloak_password_first">Keycloak Admin Password</label>
                    <input type="password" id="keycloak_password_first"></input>
                    <label for="keycloak_password">Confirm Keycloak Admin Password</label>
                    <input type="password" id="keycloak_password" name="keycloak_password"></input>
                </p>
                <div id="password_status" class="error"></div>
            </fieldset>
            <div id="form_errors" class="error"></div>
            <button type="submit" id="install_submit">Start Installation!</button>

        </form>
    )
}