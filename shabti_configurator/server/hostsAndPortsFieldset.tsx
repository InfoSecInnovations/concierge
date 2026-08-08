import getEnvs from "./getEnvs";

// the install form and the settings management form can both be on the page at once, so the
// ids are prefixed to keep them unique. The names don't need it as they're separate forms.
// submitLabel adds a button for the management form, the install form submits everything at
// once with its own button instead
export const HostsAndPortsFieldset = async (props: {
	idPrefix?: string;
	submitLabel?: string;
}) => {
	const prefix = props.idPrefix || "";
	const envs = await getEnvs();
	return (
		<fieldset>
			<legend>Hosts and Ports</legend>
			<p>
				<label for={`${prefix}web-host`}>Web Host</label>
				<input
					type="text"
					name="web-host"
					id={`${prefix}web-host`}
					value={envs.WEB_HOST || "localhost"}
				></input>
			</p>
			<p>
				<small>
					This should be the URL from which the Shabti Web UI is being accessed.
					Leave it as "localhost" unless you need to access Shabti from another
					machine.
				</small>
			</p>
			<p>
				<label for={`${prefix}web-port`}>Web Port</label>
				<input
					type="number"
					name="web-port"
					id={`${prefix}web-port`}
					value={envs.WEB_PORT || "15130"}
				></input>
			</p>
			<p>
				<small>The Shabti Web UI will be served on this port.</small>
			</p>
			<p>
				<label for={`${prefix}api-host`}>API Host</label>
				<input
					type="text"
					name="api-host"
					id={`${prefix}api-host`}
					value={envs.API_HOST || "localhost"}
				></input>
			</p>
			<p>
				<small>
					This should be the URL from which the Shabti API is being accessed.
					Leave it as "localhost" unless you need to access Shabti from another
					machine.
				</small>
			</p>
			<p>
				<label for={`${prefix}api-port`}>API Port</label>
				<input
					type="number"
					name="api-port"
					id={`${prefix}api-port`}
					value={envs.API_PORT || "15131"}
				></input>
			</p>
			<p>
				<small>The Shabti API will be served on this port.</small>
			</p>
			{props.submitLabel && <button type="submit">{props.submitLabel}</button>}
		</fieldset>
	);
};
