import semver from "semver";
import { releaseTag } from "./registry";
import { git } from "./repo";

export interface Baseline {
	tag?: string;
	warning?: string;
}

const tagExists = async (tag: string) =>
	(await git("rev-parse", "--verify", "--quiet", `refs/tags/${tag}^{commit}`))
		.exitCode === 0;

/**
 * What to diff against: the release tag for the version this branch currently declares. That is the
 * same idea as diffing a python package against the artifact published for its declared version, and
 * it is branch safe - branch 0.9.0 declares 0.8.0, so it diffs against shabti-v0.8.0 rather than
 * against whatever was released most recently somewhere else.
 */
export const resolveBaseline = async (
	rootVersion: string,
): Promise<Baseline> => {
	const exact = releaseTag(rootVersion);
	if (await tagExists(exact)) return { tag: exact };

	// only our own release tags: the repository also holds shabti_launcher-v*, v0.4.0 and 0.7a12
	const { stdout } = await git("tag", "--list", `${releaseTag("")}*`);
	const candidates = stdout
		.split("\n")
		.map((tag) => tag.trim())
		.filter(Boolean)
		.map((tag) => ({ tag, version: tag.slice(releaseTag("").length) }))
		.filter(({ version }) => !!semver.valid(version))
		.sort((a, b) => semver.rcompare(a.version, b.version));
	if (!candidates.length)
		return {
			warning:
				"no release tags found, treating every component as changed (first release)",
		};
	const fallback =
		candidates.find(({ version }) => semver.lte(version, rootVersion)) ??
		candidates[0];
	return {
		tag: fallback.tag,
		warning: `${exact} does not exist, diffing against ${fallback.tag} instead`,
	};
};

/**
 * Whether any of these paths differ from the baseline tag. A two dot diff against the tag's tree
 * rather than a range, because the tag is not necessarily an ancestor of the branch being released.
 */
export const pathsChanged = async (tag: string, paths: string[]) => {
	const { exitCode, stderr } = await git(
		"diff",
		"--quiet",
		tag,
		"--",
		...paths,
	);
	if (exitCode === 0) return false;
	if (exitCode === 1) return true;
	throw new Error(
		`could not diff ${paths.join(", ")} against ${tag}: ${stderr.trim()}`,
	);
};
