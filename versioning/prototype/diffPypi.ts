import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { pypiFiles, pypiProject, pypiSdist } from "./published";
import { absolute, run } from "./repo";

export type PyPiReason =
	| "unchanged"
	| "intrinsic"
	| "firstPublish"
	| "declaredVersionUnpublished"
	| "noSdist";

export interface PyPiComparison {
	changed: boolean;
	reason: PyPiReason;
	warning?: string;
}

const hashTree = async (root: string) => {
	const hashes = new Map<string, string>();
	for await (const entry of new Bun.Glob("**/*").scan({
		cwd: root,
		onlyFiles: true,
		dot: true,
	})) {
		const relative = entry.replaceAll("\\", "/");
		// strip the <name>-<version>/ directory every sdist is wrapped in: it necessarily differs
		const inSdist = relative.split("/").slice(1).join("/");
		// written by the build backend and holds the version, so it can never match
		if (!inSdist || inSdist === "PKG-INFO") continue;
		hashes.set(
			inSdist,
			new Bun.CryptoHasher("sha256")
				.update(await Bun.file(path.join(root, entry)).bytes())
				.digest("hex"),
		);
	}
	return hashes;
};

const extract = async (archive: string, into: string) => {
	await fs.mkdir(into, { recursive: true });
	await run(["tar", "-xzf", archive, "-C", into]);
	return hashTree(into);
};

const differ = (a: Map<string, string>, b: Map<string, string>) =>
	a.size !== b.size || [...a].some(([file, hash]) => b.get(file) !== hash);

/**
 * Whether a python package differs from what is on PyPI. Non dev installs pull these from PyPI, so
 * the published artifact, not the last release commit, is what a change has to be measured against.
 *
 * The comparison is between the sdist built from the working tree and the sdist published under the
 * version this branch declares, as a map of path to content hash: tarball bytes are not reproducible,
 * so member order, timestamps and modes all have to be ignored.
 */
export const comparePyPi = async (
	name: string,
	dir: string,
	version: string,
): Promise<PyPiComparison> => {
	if (!(await pypiProject(name)))
		return {
			changed: false,
			reason: "firstPublish",
			warning: `${name} has never been published, releasing its declared version ${version} as is`,
		};
	const published = await pypiSdist(name, version);
	if (!published) {
		// either a human bumped this by hand or a previous release run never got as far as publishing
		// it: bumping again would strand a version number
		const files = await pypiFiles(name, version);
		return files?.length
			? {
					changed: true,
					reason: "noSdist",
					warning: `${name} ${version} is published without an sdist, so it cannot be compared: bumping to be safe`,
				}
			: {
					changed: false,
					reason: "declaredVersionUnpublished",
					warning: `${name} ${version} is not on PyPI yet, releasing it as is`,
				};
	}
	const temp = await fs.mkdtemp(path.join(os.tmpdir(), "shabti-versioning-"));
	try {
		const localDir = path.join(temp, "built");
		await run(["uv", "build", "--sdist", "-o", localDir], {
			cwd: absolute(dir),
		});
		const [built] = (await fs.readdir(localDir)).filter((file) =>
			file.endsWith(".tar.gz"),
		);
		if (!built) throw new Error(`uv build produced no sdist for ${name}`);
		const downloaded = path.join(temp, "published.tar.gz");
		const res = await fetch(published.url);
		if (!res.ok)
			throw new Error(
				`could not download ${published.url}: ${res.status} ${res.statusText}`,
			);
		await Bun.write(downloaded, res);
		const [local, remote] = await Promise.all([
			extract(path.join(localDir, built), path.join(temp, "local")),
			extract(downloaded, path.join(temp, "remote")),
		]);
		return differ(local, remote)
			? { changed: true, reason: "intrinsic" }
			: { changed: false, reason: "unchanged" };
	} finally {
		await fs.rm(temp, { recursive: true, force: true });
	}
};
