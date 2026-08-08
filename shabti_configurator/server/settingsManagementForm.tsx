import { HostsAndPortsFieldset } from "./hostsAndPortsFieldset";
import { LoggingFieldset } from "./loggingFieldset";

// a form each so applying one settings area doesn't submit the values of the other
export const SettingsManagementForm = () => (
	<>
		<form action="/manage-logging" method="post">
			<LoggingFieldset
				idPrefix="manage_"
				submitLabel="Apply Settings"
			></LoggingFieldset>
		</form>
		<form action="/manage-hosts" method="post">
			<HostsAndPortsFieldset
				idPrefix="manage_"
				submitLabel="Apply Settings"
			></HostsAndPortsFieldset>
		</form>
	</>
);
