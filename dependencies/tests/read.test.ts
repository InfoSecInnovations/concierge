import { describe, expect, test } from "bun:test";
import { useRepo } from "../../versioning/tests/fixture";
import { exemption, readExceptions } from "../exceptions";
import { group, readPins } from "../read";

const ROOT_PACKAGE = `{
	"name": "shabti",
	"workspaces": ["shabti_cli/"],
	"devDependencies": { "@types/bun": "latest" },
	"dependencies": {
		"commander": "^15.0.0",
		"dotenv": "^17.2.2",
		"semver": "^7.7.4",
		"@infosecinnovations/shabti-api-client": "workspace:*"
	},
	"version": "0.8.0"
}
`;

const CLI_PACKAGE = `{
	"name": "shabti_cli",
	"devDependencies": { "@types/bun": "latest" },
	"dependencies": {
		"commander": "^14.0.2",
		"dotenv": "^16.5.0",
		"openid-client": "^6.4.2"
	},
	"version": "0.1.0"
}
`;

const NODE_CLIENT = `{
	"name": "@infosecinnovations/shabti-api-client",
	"dependencies": { "openid-client": "^6.4.2" },
	"version": "0.1.0"
}
`;

const API_PYPROJECT = `[project]
name = "shabti-api"
version = "0.1.0"
dependencies = [
    "python-keycloak~=5.8.1",
    "opensearch-py~=3.0.0",
    "shabti-keycloak",
]

[dependency-groups]
dev = ["pytest~=8.4.2"]
`;

const KEYCLOAK_PYPROJECT = `[project]
name = "shabti-keycloak"
version = "0.1.0"
dependencies = ["python-keycloak~=5.8.1"]

[build-system]
requires = ["hatchling"]
`;

const ROOT_PYPROJECT = `[project]
name = "shabti"
version = "0.1.0"
dependencies = ["pytest~=8.4.1", "ruff~=0.12.11"]
`;

const COMPOSE = `services:
  opensearch:
    image: opensearchproject/opensearch:3.5.0
  dashboards:
    image: opensearchproject/opensearch-dashboards:3.5.0
  shabti:
    image: infosecinnovations/shabti:latest
  web:
    image: infosecinnovations/shabti-web:0.1.0
  zip:
    image: javieraviles/zip
`;

const FILES = {
	"package.json": ROOT_PACKAGE,
	"pyproject.toml": ROOT_PYPROJECT,
	"shabti_cli/package.json": CLI_PACKAGE,
	"shabti_api_client_node/package.json": NODE_CLIENT,
	"docker_containers/shabti_api/pyproject.toml": API_PYPROJECT,
	"python_packages/shabti_keycloak/pyproject.toml": KEYCLOAK_PYPROJECT,
	"docker-compose.yml": COMPOSE,
};

describe("readPins", () => {
	const repo = useRepo({ packages: [], files: FILES });

	test("excludes our own packages, detected from the manifests", async () => {
		const ids = (await readPins(repo.dir)).map((pin) => pin.id);
		// declared by shabti_api_client_node/package.json, so the workspace link is ours
		expect(ids).not.toContain("@infosecinnovations/shabti-api-client");
		// declared by python_packages/shabti_keycloak/pyproject.toml
		expect(ids).not.toContain("shabti-keycloak");
	});

	test("excludes our own images by namespace", async () => {
		const ids = (await readPins(repo.dir)).map((pin) => pin.id);
		expect(ids).not.toContain("infosecinnovations/shabti");
		expect(ids).not.toContain("infosecinnovations/shabti-web");
	});

	test("keeps every third party pin", async () => {
		expect(
			[...new Set((await readPins(repo.dir)).map((pin) => pin.id))].sort(),
		).toEqual([
			"@types/bun",
			"commander",
			"dotenv",
			"hatchling",
			"javieraviles/zip",
			"openid-client",
			"opensearch-py",
			"opensearchproject/opensearch",
			"opensearchproject/opensearch-dashboards",
			"pytest",
			"python-keycloak",
			"ruff",
			"semver",
		]);
	});
});

describe("group", () => {
	const repo = useRepo({ packages: [], files: FILES });

	const find = async (id: string) => {
		const dependency = group(await readPins(repo.dir)).find(
			(candidate) => candidate.id === id,
		);
		if (!dependency) throw new Error(`no ${id} in the fixture`);
		return dependency;
	};

	test("collapses a dependency to one row however many files name it", async () => {
		const keycloak = await find("python-keycloak");
		expect(keycloak.occurrences).toHaveLength(2);
		expect(keycloak.agreement).toBe("agreed");
		expect(keycloak.versions).toEqual(["5.8.1"]);
	});

	test("flags files that name different versions", async () => {
		// pytest is ~=8.4.1 at the root and ~=8.4.2 in the container, a real divergence today
		const pytest = await find("pytest");
		expect(pytest.agreement).toBe("diverged");
		expect(pytest.versions).toEqual(["8.4.1", "8.4.2"]);
	});

	test("flags files whose ranges disagree even when neither names a version", async () => {
		for (const id of ["commander", "dotenv"]) {
			const dependency = await find(id);
			expect(dependency.agreement).toBe("diverged");
			expect(dependency.versions).toEqual([]);
		}
	});

	test("treats a dist-tag repeated everywhere as agreement", async () => {
		const types = await find("@types/bun");
		expect(types.occurrences).toHaveLength(2);
		expect(types.agreement).toBe("agreed");
		expect(types.precision).toBe("tag");
	});

	test("reports the least precise pin of the group", async () => {
		expect((await find("openid-client")).precision).toBe("range");
		expect((await find("hatchling")).precision).toBe("absent");
	});

	test("keeps the two coupled opensearch images apart", async () => {
		// they follow a coupled scheme upstream but they are two repositories, so they are two rows
		expect((await find("opensearchproject/opensearch")).versions).toEqual([
			"3.5.0",
		]);
		expect(
			(await find("opensearchproject/opensearch-dashboards")).versions,
		).toEqual(["3.5.0"]);
	});

	test("carries the registry and repository for an image", async () => {
		expect((await find("opensearchproject/opensearch")).image).toEqual({
			registry: null,
			repository: "opensearchproject/opensearch",
		});
	});

	test("orders by ecosystem then name, so a report is stable", async () => {
		const ecosystems = group(await readPins(repo.dir)).map(
			(dependency) => dependency.ecosystem,
		);
		expect(ecosystems).toEqual([...ecosystems].sort());
	});
});

describe("exceptions", () => {
	const repo = useRepo({
		packages: [],
		files: {
			...FILES,
			"dependencies/exceptions.json": JSON.stringify({
				exceptions: [
					{
						ecosystem: "node",
						name: "@types/bun",
						reason: "tracks the Bun the repo is built with",
					},
					{
						ecosystem: "python",
						name: "hatchling",
						reason: "a build requirement of a published library",
						files: ["python_packages/shabti_keycloak/pyproject.toml"],
					},
					{
						ecosystem: "docker",
						name: "javieraviles/zip",
						reason: "only used to zip the Keycloak policies and never deployed",
					},
				],
			}),
		},
	});

	test("covers a dependency listed for every file", async () => {
		const exceptions = await readExceptions(repo.dir);
		const pins = (await readPins(repo.dir)).filter(
			(pin) => pin.id === "@types/bun",
		);
		expect(pins).toHaveLength(2);
		expect(pins.every((pin) => exemption(exceptions, pin))).toBe(true);
	});

	test("covers only the files a scoped exception names", async () => {
		const exceptions = await readExceptions(repo.dir);
		const hatchling = (await readPins(repo.dir)).find(
			(pin) => pin.id === "hatchling",
		);
		expect(
			exemption(exceptions, hatchling as NonNullable<typeof hatchling>),
		).toBeTruthy();
		expect(
			exemption(exceptions, {
				...(hatchling as NonNullable<typeof hatchling>),
				file: "docker_containers/shabti_api/pyproject.toml",
			}),
		).toBeUndefined();
	});

	test("does not cover anything else", async () => {
		const exceptions = await readExceptions(repo.dir);
		const commander = (await readPins(repo.dir)).find(
			(pin) => pin.id === "commander",
		);
		expect(
			exemption(exceptions, commander as NonNullable<typeof commander>),
		).toBeUndefined();
	});

	test("is optional", async () => {
		// a repo with no exceptions file is a valid state, and most fixtures rely on it
		expect(await readExceptions(`${repo.dir}/does-not-exist`)).toEqual([]);
	});

	test("covers an image, which has no version to pin at all", async () => {
		const exceptions = await readExceptions(repo.dir);
		const zip = (await readPins(repo.dir)).find(
			(pin) => pin.id === "javieraviles/zip",
		);
		expect(zip?.ecosystem).toBe("docker");
		expect(zip?.precision).toBe("absent");
		expect(
			exemption(exceptions, zip as NonNullable<typeof zip>)?.reason,
		).toMatch(/never deployed/);
	});

	test("refuses an ecosystem it does not know", async () => {
		// a misspelling would match no pin and exempt nothing, which looks just like it working
		await repo.write(
			"dependencies/exceptions.json",
			JSON.stringify({
				exceptions: [
					{ ecosystem: "dockerr", name: "x", reason: "typo in the ecosystem" },
				],
			}),
		);
		await expect(readExceptions(repo.dir)).rejects.toThrow(
			/names ecosystem "dockerr"/,
		);
	});

	test("refuses an entry with no reason", async () => {
		await repo.write(
			"dependencies/exceptions.json",
			JSON.stringify({ exceptions: [{ ecosystem: "node", name: "x" }] }),
		);
		await expect(readExceptions(repo.dir)).rejects.toThrow(
			/needs an ecosystem/,
		);
	});
});
