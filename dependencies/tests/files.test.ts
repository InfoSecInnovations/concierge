import { describe, expect, test } from "bun:test";
import { useRepo } from "../../versioning/tests/fixture";
import { ecosystemOf, kindOf, pinFiles } from "../files";
import type { Kind } from "../types";

describe("kindOf", () => {
	const cases: [string, Kind | null][] = [
		["package.json", "node"],
		["shabti_cli/package.json", "node"],
		["pyproject.toml", "python"],
		["docker_containers/shabti_api/pyproject.toml", "python"],
		["requirements.txt", "python"],
		["requirements-dev.txt", "python"],
		// every compose basename the repo actually uses, plus the compose spec's own defaults
		["docker-compose.yml", "compose"],
		["docker_containers/docker-compose-uv-lock.yml", "compose"],
		["docker-compose-keycloak.yml", "compose"],
		["docker-compose-zip-policy.yml", "compose"],
		["compose.yml", "compose"],
		["compose.yaml", "compose"],
		["Dockerfile", "dockerfile"],
		["docker_containers/shabti_api/Dockerfile", "dockerfile"],
		["Dockerfile.api", "dockerfile"],
		// a pin here would be a resolved transitive dependency, which is the one thing to never report
		["bun.lock", null],
		["uv.lock", null],
		["package-lock.json", null],
		["yarn.lock", null],
		["poetry.lock", null],
		// the near misses: none of these is a compose file or a Dockerfile
		[".pre-commit-config.yaml", null],
		[".github/workflows/publish_shabti.yml", null],
		[".github/actions/get_pyproject_version/action.yml", null],
		["biome.json", null],
		["shabti-components.json", null],
		["configurator-versions.json", null],
		["tsconfig.json", null],
		["Dockerfile.dockerignore", null],
		[".dockerignore", null],
		["README.md", null],
	];

	for (const [file, expected] of cases)
		test(`${file} -> ${expected}`, () => {
			expect(kindOf(file)).toBe(expected);
		});
});

describe("ecosystemOf", () => {
	test("folds both docker spellings into one ecosystem", () => {
		expect(ecosystemOf("compose")).toBe("docker");
		expect(ecosystemOf("dockerfile")).toBe("docker");
		expect(ecosystemOf("node")).toBe("node");
		expect(ecosystemOf("python")).toBe("python");
	});
});

describe("pinFiles", () => {
	const repo = useRepo({
		packages: [],
		files: {
			".gitignore": "dist\nnode_modules\n",
			"pyproject.toml": '[project]\nname = "root"\nversion = "0.1.0"\n',
			"docker-compose.yml": "services:\n  db:\n    image: postgres:18.3\n",
			"containers/Dockerfile": "FROM astral/uv:0.11.1\n",
			"containers/Dockerfile.dockerignore": "**/.git\n",
			// build output: a stale copy of a compose file, naming images the repo stopped using
			"dist/docker-compose.yml":
				"services:\n  ai:\n    image: ollama/ollama:latest\n",
			"dist/package.json": '{ "dependencies": { "gone": "1.0.0" } }\n',
			"node_modules/left-pad/package.json": '{ "name": "left-pad" }\n',
			// not a pin file, and must not become one
			"uv.lock": "version = 1\n",
			"README.md": "# fixture\n",
		},
	});

	test("finds every pin file and nothing else", async () => {
		expect(await pinFiles(repo.dir)).toEqual([
			{ file: "containers/Dockerfile", kind: "dockerfile" },
			{ file: "docker-compose.yml", kind: "compose" },
			{ file: "package.json", kind: "node" },
			{ file: "pyproject.toml", kind: "python" },
		]);
	});

	test("ignores gitignored build output", async () => {
		// the real hazard: shabti_configurator/dist holds stale compose copies with ollama and
		// unstructured images, so a glob would invent dependencies and see divergence that is not there
		const found = (await pinFiles(repo.dir)).map(({ file }) => file);
		expect(found.some((file) => file.startsWith("dist/"))).toBe(false);
		expect(found.some((file) => file.startsWith("node_modules/"))).toBe(false);
	});

	test("finds a pin file that is untracked but not ignored", async () => {
		await repo.write(
			"extra/docker-compose-new.yml",
			"services:\n  x:\n    image: postgres:18.3\n",
		);
		expect(await pinFiles(repo.dir)).toContainEqual({
			file: "extra/docker-compose-new.yml",
			kind: "compose",
		});
	});
});
