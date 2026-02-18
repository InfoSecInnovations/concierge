import listCompatibleDockerTags from "./listCompatibleDockerTags";

export const VersionSelector = async (props: {
	devMode: boolean;
}) => {
	const availableVersions = await listCompatibleDockerTags();
	return (
		<select>
			{props.devMode && <option value="local">local</option>}
			{availableVersions.map((version) => (
				<option value={version}>{version}</option>
			))}
		</select>
	);
};
