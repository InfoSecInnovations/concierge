import { describe, expect, test } from "bun:test";
import type { Exception } from "../exceptions";
import { type Result, migratablePins, render } from "../migrate";
import type { Pin } from "../types";

const result = (extra: Partial<Result> = {}): Result => ({
	migrations: [],
	skipped: [],
	floating: [],
	files: [],
	locked: [],
	...extra,
});

const fastapi = {
	name: "fastapi",
	ecosystem: "python" as const,
	from: ["~=0.136.0"],
	to: "0.137.0",
	files: ["pyproject.toml"],
};

describe("migrating rows", () => {
	test("show the pin, what it becomes, and where it is", () => {
		const text = render(result({ migrations: [fastapi] }), { dryRun: true });
		expect(text).toContain("migrating");
		expect(text).toContain("python");
		expect(text).toContain("~=0.136.0 -> 0.137.0");
		expect(text).toContain("pyproject.toml");
		expect(text).toContain("1 to migrate, 0 skipped, 0 left floating");
	});

	test("say the pin once however many files repeat it", () => {
		const text = render(
			result({
				migrations: [
					{
						name: "commander",
						ecosystem: "node",
						from: ["^14.0.0", "^14.0.0", "^14.0.0"],
						to: "14.0.1",
						files: [
							"package.json",
							"shabti_cli/package.json",
							"api/package.json",
						],
					},
				],
			}),
			{ dryRun: true },
		);
		expect(text).toContain("^14.0.0 -> 14.0.1");
		expect(text).toContain("3 files");
	});
});

describe("skipped rows", () => {
	test("give the kind, not the sentence that goes to stderr", () => {
		const text = render(
			result({
				skipped: [
					{
						name: "shiny",
						ecosystem: "python",
						kind: "uninstalled",
						from: [">=1.6.0"],
						reason:
							"no locked version found for python_packages/shiny/pyproject.toml - install first, or it is a library with no lockfile",
					},
					{
						name: "commander",
						ecosystem: "node",
						kind: "diverged",
						from: ["^14.0.0", "^11.0.0"],
						reason:
							"resolves to 14.0.1 and 11.1.0 in different places, so pick one with set",
					},
				],
			}),
			{ dryRun: true },
		);
		expect(text).toContain("not installed");
		expect(text).toContain("resolves differently");
		expect(text).toContain("^14.0.0, ^11.0.0");
		expect(text).not.toContain("library with no lockfile");
		expect(text).toContain("0 to migrate, 2 skipped, 0 left floating");
	});
});

describe("the exempt are listed but never given a version", () => {
	test("a floating row shows the pin it keeps and nothing to bump it to", () => {
		const text = render(
			result({
				migrations: [fastapi],
				floating: [
					{
						name: "@types/bun",
						ecosystem: "node",
						from: ["^1.3.4"],
						files: ["package.json"],
					},
				],
			}),
			{ dryRun: true },
		);
		const floating = text
			.split("\n")
			.find((line) => line.includes("@types/bun")) as string;
		expect(text).toContain("intentionally floating, not migrated");
		expect(floating).toContain("^1.3.4");
		// the version it would have been bumped to is the one thing that must not happen to it
		expect(floating).not.toContain("->");
		expect(text).toContain("1 to migrate, 0 skipped, 1 left floating");
	});
});

describe("exempt pins are dropped before anything is planned", () => {
	const pin = (extra: Partial<Pin> = {}): Pin => ({
		name: "pydantic",
		id: "pydantic",
		ecosystem: "python",
		file: "python_packages/shabti_types/pyproject.toml",
		line: 1,
		specifier: ">=2.0.0",
		raw: "pydantic>=2.0.0",
		version: "2.0.0",
		precision: "range",
		extras: [],
		marker: null,
		location: "project.dependencies",
		...extra,
	});

	const exception = (files?: string[]): Exception => ({
		ecosystem: "python",
		name: "pydantic",
		reason: "a dependency of a published library",
		files,
	});

	test("an exception with no files exempts every occurrence", () => {
		expect(
			migratablePins(
				[pin(), pin({ file: "api/pyproject.toml" })],
				[exception()],
			),
		).toEqual([]);
	});

	test("an exception with files exempts only those, so the rest still migrates", () => {
		const app = pin({ file: "api/pyproject.toml" });
		expect(
			migratablePins(
				[pin(), app],
				[exception(["python_packages/shabti_types/pyproject.toml"])],
			),
		).toEqual([app]);
	});

	test("an unrelated exception exempts nothing", () => {
		const pins = [pin()];
		expect(migratablePins(pins, [{ ...exception(), name: "httpx" }])).toEqual(
			pins,
		);
	});
});

describe("what happened to the tree", () => {
	test("a dry run says nothing was written", () => {
		expect(
			render(result({ migrations: [fastapi] }), { dryRun: true }),
		).toContain("dry run, nothing written");
	});

	test("a run says what it wrote and what it locked", () => {
		const text = render(
			result({
				migrations: [fastapi],
				files: ["pyproject.toml"],
				locked: ["uv lock"],
			}),
		);
		expect(text).toContain("wrote 1 file\nran uv lock");
	});

	test("--no-lock says what is left to run rather than claiming it ran", () => {
		const text = render(
			result({
				migrations: [fastapi],
				files: ["pyproject.toml"],
				locked: ["uv lock"],
			}),
			{ lock: false },
		);
		expect(text).toContain("wrote 1 file\nto lock, run: uv lock");
	});

	test("an empty section prints no heading", () => {
		const lines = render(result(), { dryRun: true }).split("\n");
		expect(lines).not.toContain("migrating");
		expect(lines).not.toContain("skipped");
	});
});
