import { describe, expect, test } from "bun:test";
import { parseRequirement, precisionOf, pythonPins } from "../python";
import type { Precision } from "../types";

describe("parseRequirement", () => {
	const cases: [
		string,
		{
			name: string;
			extras: string[];
			specifier: string;
			marker: string | null;
		} | null,
	][] = [
		[
			"fastapi[standard]~=0.136.3",
			{
				name: "fastapi",
				extras: ["standard"],
				specifier: "~=0.136.3",
				marker: null,
			},
		],
		[
			"pytest~=8.4.1",
			{ name: "pytest", extras: [], specifier: "~=8.4.1", marker: null },
		],
		[
			"humanize==4.15.0",
			{ name: "humanize", extras: [], specifier: "==4.15.0", marker: null },
		],
		[
			"shiny>=1.5.1",
			{ name: "shiny", extras: [], specifier: ">=1.5.1", marker: null },
		],
		// the four dependencies this repo declares with no version at all
		["zxcvbn", { name: "zxcvbn", extras: [], specifier: "", marker: null }],
		["pydantic", { name: "pydantic", extras: [], specifier: "", marker: null }],
		["pyyaml", { name: "pyyaml", extras: [], specifier: "", marker: null }],
		[
			"hatchling",
			{ name: "hatchling", extras: [], specifier: "", marker: null },
		],
		[
			"requests>=2,<3",
			{ name: "requests", extras: [], specifier: ">=2,<3", marker: null },
		],
		["foo==1.*", { name: "foo", extras: [], specifier: "==1.*", marker: null }],
		[
			"foo===1.0",
			{ name: "foo", extras: [], specifier: "===1.0", marker: null },
		],
		// spaces, capitals and an underscore, the shape versioning/tests already fixtures
		[
			"Python_Lib == 0.1.0",
			{ name: "Python_Lib", extras: [], specifier: "== 0.1.0", marker: null },
		],
		[
			'foo; python_version < "3.13"',
			{
				name: "foo",
				extras: [],
				specifier: "",
				marker: 'python_version < "3.13"',
			},
		],
		[
			'foo~=1.0 ; sys_platform == "win32"',
			{
				name: "foo",
				extras: [],
				specifier: "~=1.0",
				marker: 'sys_platform == "win32"',
			},
		],
		[
			"foo[a,b]~=1.0",
			{ name: "foo", extras: ["a", "b"], specifier: "~=1.0", marker: null },
		],
		// a direct reference gets its version from a URL, so there is no registry to check
		["foo @ https://example.com/foo.whl", null],
		["", null],
		["# a comment", null],
	];

	for (const [requirement, expected] of cases)
		test(JSON.stringify(requirement), () => {
			expect(parseRequirement(requirement)).toEqual(expected);
		});
});

describe("precisionOf", () => {
	const cases: [string, Precision, string | null][] = [
		["==4.15.0", "exact", "4.15.0"],
		["== 0.1.0", "exact", "0.1.0"],
		["===1.0", "exact", "1.0"],
		["~=8.4.1", "compatible", "8.4.1"],
		[">=1.5.1", "range", null],
		[">1.0", "range", null],
		["<=2.0", "range", null],
		["!=1.0", "range", null],
		// never guess which clause of a set is the version
		[">=2,<3", "range", null],
		["~=1.0,!=1.2", "range", null],
		// an equals sign with a wildcard is a range wearing a disguise
		["==1.*", "range", null],
		["", "absent", null],
		["   ", "absent", null],
	];

	for (const [specifier, precision, version] of cases)
		test(`${JSON.stringify(specifier)} -> ${precision}`, () => {
			expect(precisionOf(specifier)).toEqual({ precision, version });
		});
});

/** the shabti_api shape: compatible pins, extras, a dependency group and unversioned internal deps */
const PYPROJECT = `[project]
name = "shabti-api"
version = "0.1.0"
requires-python = ">=3.14, <3.15"
dependencies = [
    "fastapi[standard]~=0.136.3",
    "opensearch-py~=3.0.0",
    "requests~=2.33.1",
    "shabti-util",
]

[project.optional-dependencies]
gpu = [
    "torch~=2.5.0",
]

[dependency-groups]
dev = [
    "pytest~=8.4.2",
    "pytest-asyncio~=1.2.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.uv.sources]
shabti-util = { path = "/app/python_packages/shabti_util", editable = true }
`;

describe("pythonPins", () => {
	const pins = pythonPins(
		"docker_containers/shabti_api/pyproject.toml",
		PYPROJECT,
	);
	const byName = (name: string) => pins.find((pin) => pin.name === name);

	test("finds every requirement from every kind of list", () => {
		expect(pins.map((pin) => pin.name).sort()).toEqual([
			"fastapi",
			"hatchling",
			"opensearch-py",
			"pytest",
			"pytest-asyncio",
			"requests",
			"shabti-util",
			"torch",
		]);
	});

	test("records where each one was declared", () => {
		expect(byName("fastapi")?.location).toBe("project.dependencies");
		expect(byName("torch")?.location).toBe("project.optional-dependencies.gpu");
		expect(byName("pytest")?.location).toBe("dependency-groups.dev");
		// a build requirement is a third party dependency too, and hatchling is unpinned in five files
		expect(byName("hatchling")?.location).toBe("build-system.requires");
	});

	test("keeps extras so a rewrite can put them back", () => {
		expect(byName("fastapi")?.extras).toEqual(["standard"]);
		expect(byName("fastapi")?.specifier).toBe("~=0.136.3");
		expect(byName("fastapi")?.version).toBe("0.136.3");
		expect(byName("fastapi")?.precision).toBe("compatible");
	});

	test("reports an unversioned requirement as unpinned rather than skipping it", () => {
		expect(byName("hatchling")?.precision).toBe("absent");
		expect(byName("hatchling")?.version).toBeNull();
		expect(byName("shabti-util")?.precision).toBe("absent");
	});

	test("normalises the id but keeps the spelling", () => {
		const pin = pythonPins(
			"pyproject.toml",
			'[project]\ndependencies = ["Python_Lib==1.0"]\n',
		)[0];
		expect(pin?.name).toBe("Python_Lib");
		expect(pin?.id).toBe("python-lib");
	});

	test("recovers the line each one is written on", () => {
		expect(byName("fastapi")?.line).toBe(6);
		expect(byName("pytest-asyncio")?.line).toBe(20);
	});

	test("refuses a manifest it cannot parse", () => {
		expect(() => pythonPins("pyproject.toml", "[project\nname =")).toThrow(
			/could not parse pyproject\.toml/,
		);
	});
});

describe("pythonPins over a requirements file", () => {
	const REQUIREMENTS = `# runtime
fastapi[standard]==0.136.3
requests==2.33.1  # pinned for the api
-r other.txt
--index-url https://example.com/simple

pyyaml
`;

	test("reads one requirement per line, minus comments and options", () => {
		const pins = pythonPins("requirements.txt", REQUIREMENTS);
		expect(pins.map((pin) => [pin.name, pin.version, pin.line])).toEqual([
			["fastapi", "0.136.3", 2],
			["requests", "2.33.1", 3],
			["pyyaml", null, 7],
		]);
		expect(pins.every((pin) => pin.location === "requirements")).toBe(true);
	});
});
