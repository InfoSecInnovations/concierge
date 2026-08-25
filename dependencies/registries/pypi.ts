/**
 * What PyPI has published for a project.
 *
 * Read through the Simple JSON API rather than the older /pypi/<name>/json. It is the only one of the
 * two that hands back a ready made version list, it is markedly smaller (ruff is 783 KB gzipped against
 * 6 MB), and the `releases` map the older endpoint is built on is slated for removal.
 *
 * The one thing it does not give directly is whether a version is yanked, because yanking is per file.
 * A version counts as yanked only when every file attributed to it is, which is what keeps a project
 * that yanked one wheel of a release from looking as though it withdrew the release.
 */

import { normalise } from "../../versioning/manifest";
import type { Client } from "../http";
import { type Version, compare, parse } from "../pep440";
import { assemble, unreadableNote } from "../releases";
import type { Catalogue } from "../types";

const ACCEPT = "application/vnd.pypi.simple.v1+json";

type SimpleFile = { filename?: string; yanked?: boolean | string };

type SimpleProject = {
	name?: string;
	versions?: string[];
	files?: SimpleFile[];
	"project-status"?: { status?: string };
};

/**
 * The version a distribution filename carries. Wheels put it in the second dash separated field, and an
 * sdist puts it after the last dash, which is what copes with a project name containing one. Passed
 * through the version parser afterwards, so a historic filename that was never normalised still lands
 * on the same version as its neighbours.
 */
const versionInFilename = (filename: string) => {
	if (/\.(whl|egg)$/i.test(filename))
		return filename.slice(0, filename.lastIndexOf(".")).split("-")[1];
	const stripped = filename.replace(/\.(tar\.gz|tar\.bz2|tgz|zip)$/i, "");
	if (stripped === filename) return undefined;
	const at = stripped.lastIndexOf("-");
	return at < 0 ? undefined : stripped.slice(at + 1);
};

/** the canonical versions every one of whose files is yanked, with the reason when one was given */
const yanked = (files: SimpleFile[]) => {
	const seen = new Map<
		string,
		{ total: number; yanked: number; reason?: string }
	>();
	for (const file of files) {
		if (!file.filename) continue;
		const raw = versionInFilename(file.filename);
		const canonical = raw ? parse(raw)?.canonical : undefined;
		// a filename shape we cannot read attributes to nothing, and so never marks anything yanked
		if (!canonical) continue;
		const counts = seen.get(canonical) ?? { total: 0, yanked: 0 };
		counts.total++;
		if (file.yanked) {
			counts.yanked++;
			if (typeof file.yanked === "string") counts.reason ??= file.yanked;
		}
		seen.set(canonical, counts);
	}
	return new Map(
		[...seen]
			.filter(([, counts]) => counts.total === counts.yanked)
			.map(([version, counts]) => [
				version,
				counts.reason ? `yanked: ${counts.reason}` : "yanked",
			]),
	);
};

export const pypiCatalogue = async (
	project: string,
	client: Client,
): Promise<Catalogue> => {
	const name = normalise(project);
	const response = await client.request(`https://pypi.org/simple/${name}/`, {
		headers: { accept: ACCEPT },
	});
	if (response.status === 404)
		throw new Error(`${name} is not published on PyPI`);
	if (!response.ok)
		throw new Error(`PyPI returned ${response.status} for ${name}`);

	const body = (await response.json()) as SimpleProject;
	const withdrawn = yanked(body.files ?? []);
	const notes: string[] = [];
	// a redirect to another name is how PyPI reports a rename, and it is worth saying out loud
	if (body.name && normalise(body.name) !== name)
		notes.push(`PyPI answered for ${body.name} rather than ${name}`);
	const status = body["project-status"]?.status;
	if (status && status !== "active")
		notes.push(`the project is marked ${status} on PyPI`);

	let unreadable = 0;
	const entries = (body.versions ?? []).flatMap((raw) => {
		const version = parse(raw);
		if (!version) {
			unreadable++;
			return [];
		}
		return [{ raw, version }];
	});

	return assemble(
		entries,
		// the tie break keeps the more precise spelling of two equal versions
		(a, b) =>
			compare(a.version, b.version) ||
			a.version.release.length - b.version.release.length,
		({ raw, version }: { raw: string; version: Version }) => ({
			version: version.canonical,
			raw: version.canonical === raw ? undefined : raw,
			prerelease: version.prerelease,
			withdrawn: withdrawn.get(version.canonical),
		}),
		[...notes, ...unreadableNote(unreadable, "PyPI")],
	);
};
