import { git } from "./git";
import { declaredVersion, versionIn } from "./manifest";

/**
 * The commit that set the version a package currently declares, or null if that version is not in
 * committed history - an uncommitted bump, or a manifest that was never committed.
 *
 * Only commits that changed the manifest are considered, so a commit that touched the package's source
 * without moving its version never becomes the answer. Walking back from the newest of those and stopping
 * at the first commit declaring something else lands on the transition into this version, and on the most
 * recent one, so a version that was adopted, dropped and adopted again resolves to the latest adoption.
 * A package whose manifest first appears already at this version resolves to the commit that added it.
 */
export const versionCommit = async (repoDir: string, packageDir: string) => {
	const { manifest, version } = await declaredVersion(repoDir, packageDir);
	const inRepo = git(repoDir);
	const { stdout } = await inRepo("log", "--format=%H", "--", manifest);
	let found: string | null = null;
	for (const commit of stdout.split("\n").filter(Boolean)) {
		// a non zero exit is the file not existing at that commit, which ends the run
		const { exitCode, stdout: text } = await inRepo(
			"show",
			`${commit}:${manifest}`,
		);
		if (exitCode !== 0 || versionIn(manifest, text) !== version) break;
		found = commit;
	}
	return found;
};
