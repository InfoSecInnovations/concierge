/**
 * Which files can carry a third party pin, and where they are.
 *
 * The list comes from git rather than from a glob or a directory walk, and that is a correctness
 * requirement rather than a convenience: shabti_configurator/dist is gitignored build output holding
 * stale copies of the compose files, complete with images the repo stopped using. A walk would report
 * them as real dependencies and would see divergence that does not exist. Asking git also skips
 * node_modules, .venv and the stray virtualenv directories at the repo root for free.
 */

import path from "node:path";
import { trackedFiles } from "../versioning/write";
import type { Ecosystem, Kind } from "./types";

const NODE = /^package\.json$/;
const PYTHON = /^(pyproject\.toml|requirements[\w.-]*\.txt)$/;
/** docker-compose.yml, docker-compose-uv-lock.yml, and the compose spec's own compose.yaml */
const COMPOSE = /^(docker-)?compose[\w.-]*\.ya?ml$/;
/** Dockerfile and Dockerfile.api, but never Dockerfile.dockerignore */
const DOCKERFILE = /^Dockerfile(\.(?!dockerignore$)[\w.-]+)?$/;
/**
 * Never read. A pin found in one of these would be a resolved transitive dependency, and reporting
 * those is exactly what this tool must not do - so the exclusion is written down rather than left to
 * the fact that no lockfile basename happens to match the patterns above.
 */
const LOCKFILES =
	/^(bun\.lockb?|uv\.lock|package-lock\.json|yarn\.lock|poetry\.lock|Pipfile\.lock)$/;

/** the shape of pin a file can hold, or null when it holds none */
export const kindOf = (file: string): Kind | null => {
	const name = path.posix.basename(file);
	if (LOCKFILES.test(name)) return null;
	if (NODE.test(name)) return "node";
	if (PYTHON.test(name)) return "python";
	if (COMPOSE.test(name)) return "compose";
	if (DOCKERFILE.test(name)) return "dockerfile";
	return null;
};

/** compose files and Dockerfiles pin the same things, so they are one ecosystem in two spellings */
export const ecosystemOf = (kind: Kind): Ecosystem =>
	kind === "node" ? "node" : kind === "python" ? "python" : "docker";

/** every file in the working tree that can carry a pin, sorted so a report is stable run to run */
export const pinFiles = async (repoDir: string) =>
	(await trackedFiles(repoDir))
		.flatMap((file) => {
			const kind = kindOf(file);
			return kind ? [{ file, kind }] : [];
		})
		.sort((a, b) => (a.file < b.file ? -1 : a.file > b.file ? 1 : 0));
