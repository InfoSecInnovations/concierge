import path from "node:path";
import getDefaultDirectory from "./getDefaultDirectory";
import getEnvs from "./getEnvs";

// the install form and the settings management form can both be on the page at once, so the
// ids are prefixed to keep them unique. The names don't need it as they're separate forms.
// submitLabel adds a button for the management form, the install form submits everything at
// once with its own button instead
export const LoggingFieldset = async (props: {
	idPrefix?: string;
	submitLabel?: string;
}) => {
	const prefix = props.idPrefix || "";
	const envs = await getEnvs();
	const loggingEnabled = envs.SHABTI_BASE_SERVICE?.endsWith("logging");
	const logDir =
		envs.SHABTI_LOG_DIR || path.join(getDefaultDirectory()!, "shabti", "logs");
	return (
		<fieldset>
			<legend>Logging</legend>
			<p>
				<input
					type="checkbox"
					id={`${prefix}activity_logging`}
					name="activity_logging"
					checked={loggingEnabled}
				></input>
				<label for={`${prefix}activity_logging`}>Enable Activity Logging</label>
			</p>
			<p class="logging_element">
				<label for={`${prefix}logging_location`}>Log Directory</label>
				<input
					type="text"
					name="logging_location"
					id={`${prefix}logging_location`}
					value={logDir}
				></input>
			</p>
			{props.submitLabel && <button type="submit">{props.submitLabel}</button>}
		</fieldset>
	);
};
