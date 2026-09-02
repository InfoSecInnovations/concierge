import { mkdir, readFile, rm } from "node:fs/promises";
import path from "node:path";
import { XMLBuilder, XMLParser } from "fast-xml-parser";
import {
	TEST_TYPES,
	SUITES,
	type TestType,
	type Suite,
	typeLabel,
	resultFile,
} from "./suites";

export const RESULTS_DIR = path.join(import.meta.dir, "test_results");
const ARCHIVE_DIR = path.join(import.meta.dir, "processed_test_runs");

export type Outcome = "passed" | "failed" | "timed out" | "skipped";

export interface Case {
	name: string;
	/** the path the runner reported, which is what the rerun hint is built from */
	file?: string;
	status: Outcome;
	message?: string;
	seconds: number;
}

export interface SuiteRun {
	testType: TestType;
	suite: Suite;
	/** absent when the suite was filtered out or its test type never ran */
	outcome?: Outcome;
	seconds: number;
	cases: Case[];
	/** set when the suite's own process failed without producing any usable JUnit output */
	note?: string;
	/** the last lines the suite printed, which is the only reason available when note is set */
	tail?: string[];
}

const bold = (text: string) => `\x1b[1m${text}\x1b[0m`;
const red = (text: string) => `\x1b[31m${text}\x1b[0m`;
const green = (text: string) => `\x1b[32m${text}\x1b[0m`;
const dim = (text: string) => `\x1b[2m${text}\x1b[0m`;

export const clearResults = async () => {
	await rm(RESULTS_DIR, { recursive: true, force: true });
	await mkdir(RESULTS_DIR, { recursive: true });
};

const asArray = <T>(value: T | T[] | undefined): T[] =>
	value === undefined ? [] : Array.isArray(value) ? value : [value];

const text = (node: unknown) => {
	if (typeof node === "string") return node;
	if (node && typeof node === "object") {
		const record = node as Record<string, unknown>;
		const message = record["@_message"] ?? record["#text"];
		if (typeof message === "string") return message;
	}
	return undefined;
};

/** pytest and bun both nest testcases under testsuite, but bun nests testsuites for describes too */
const collectCases = (node: unknown, into: Case[]) => {
	if (!node || typeof node !== "object") return;
	const record = node as Record<string, unknown>;
	for (const testcase of asArray(record.testcase)) {
		const attrs = testcase as Record<string, unknown>;
		const failure = attrs.failure ?? attrs.error;
		into.push({
			name: String(attrs["@_name"] ?? "<unnamed>"),
			file: (attrs["@_file"] ?? attrs["@_classname"]) as string | undefined,
			status: failure ? "failed" : attrs.skipped ? "skipped" : "passed",
			message: failure ? text(asArray(failure)[0]) : undefined,
			seconds: Number(attrs["@_time"] ?? 0),
		});
	}
	for (const child of asArray(record.testsuite)) collectCases(child, into);
};

/** the raw testsuite nodes, kept so the whole run can be archived as one file */
const parsedSuites: unknown[] = [];

export const readCases = async (testType: TestType, suite: Suite) => {
	const file = path.join(RESULTS_DIR, resultFile(testType, suite));
	let xml: string;
	try {
		xml = await readFile(file, "utf8");
	} catch {
		return undefined; // the runner died before writing anything
	}
	const parsed = new XMLParser({ ignoreAttributes: false }).parse(
		xml,
	) as Record<string, unknown>;
	const root = (parsed.testsuites ?? parsed) as Record<string, unknown>;
	for (const node of asArray(root.testsuite)) parsedSuites.push(node);
	const cases: Case[] = [];
	collectCases(root, cases);
	return cases;
};

export const archive = async () => {
	if (!parsedSuites.length) return undefined;
	await mkdir(ARCHIVE_DIR, { recursive: true });
	const file = path.join(
		ARCHIVE_DIR,
		`shabti_test_run_${new Date().toISOString().replace(/:/g, "_")}.xml`,
	);
	const xml = new XMLBuilder({ ignoreAttributes: false, format: true }).build({
		testsuites: { testsuite: parsedSuites },
	});
	await Bun.write(file, xml);
	return file;
};

const duration = (seconds: number) => {
	if (seconds < 60) return `${seconds.toFixed(1)}s`;
	const minutes = Math.floor(seconds / 60);
	return `${minutes}m${String(Math.round(seconds % 60)).padStart(2, "0")}s`;
};

const tally = (cases: Case[]) => {
	const counts = { passed: 0, failed: 0, skipped: 0 };
	for (const item of cases)
		if (item.status === "failed") counts.failed += 1;
		else if (item.status === "skipped") counts.skipped += 1;
		else counts.passed += 1;
	return counts;
};

/**
 * How to get back to just this failure. pytest takes a node id relative to the suite's own
 * directory; bun has no node ids, so it gets a name pattern instead.
 */
const rerun = (run: SuiteRun, failure: Case) => {
	const base = `bun run test ${run.testType} ${run.suite.id}`;
	if (run.suite.runner === "bun")
		return `${base} -t ${JSON.stringify(failure.name)}`;
	const target = run.suite.target(run.testType);
	const file = failure.file?.startsWith(`${target}/`)
		? failure.file.slice(target.length + 1)
		: failure.file;
	return file ? `${base} ${file}::${failure.name}` : base;
};

/** at most this many failures get spelled out before the rest are left to the full results */
const DETAILED_FAILURES = 15;
/** at most this many lines of one failure's message, which for a stack trace is plenty */
const MESSAGE_LINES = 6;
/**
 * How much of a suite's own output to fall back on. Wider than a message on purpose: the runner
 * prints its "0 pass, 1 fail" summary last, so a narrow window catches only that and none of the
 * error above it.
 */
const OUTPUT_LINES = 20;

/** blank lines are dropped, so a message that turns out to be empty prints nothing at all */
const indented = (lines: string[], prefix = "      ") => {
	for (const line of lines) if (line.trim()) console.log(`${prefix}${line}`);
};

const broke = (run: SuiteRun) =>
	run.outcome !== undefined &&
	run.outcome !== "passed" &&
	run.outcome !== "skipped";

/**
 * Why the run failed, in enough detail to act on without scrolling back through it. A suite that
 * died before writing any JUnit output has no test to blame, so the tail of what it printed stands
 * in for one -- that is the only record of, say, a missing binary or a bad path.
 */
const renderFailures = (runs: SuiteRun[]) => {
	const failed = runs.filter(broke);
	if (!failed.length) return;

	console.log(`\n${bold(red("FAILURES"))}\n`);
	let shown = 0;
	let held = 0;
	for (const run of failed) {
		console.log(`  ${bold(`${typeLabel[run.testType]} / ${run.suite.id}`)}`);
		const cases = run.cases.filter((item) => item.status === "failed");

		const output = (run.tail ?? []).filter((line) => line.trim());

		// nothing to blame, so what the suite printed on its way out has to serve as the reason
		if (!cases.length) {
			console.log(
				`    ${red(run.note ?? "failed")}${output.length ? ", last output:" : ""}`,
			);
			indented(output.slice(-OUTPUT_LINES));
			console.log("");
			continue;
		}

		for (const item of cases) {
			// every failing suite still gets a heading; only the per-test detail is capped
			if (shown >= DETAILED_FAILURES) {
				held += 1;
				continue;
			}
			shown += 1;
			console.log(
				`    ${red(item.file ? `${item.file}::${item.name}` : item.name)}`,
			);
			indented((item.message ?? "").trim().split("\n").slice(0, MESSAGE_LINES));
			console.log(`      ${dim(`rerun: ${rerun(run, item)}`)}`);
		}

		// bun's JUnit reporter can write a bare <failure type="AssertionError" /> carrying no
		// message, and a thrown error in a describe body always comes out that way. The console
		// output is then the only record of what actually went wrong, so fall back to it.
		if (!cases.some((item) => item.message?.trim()) && output.length) {
			console.log(`    ${dim("no message was reported; last output:")}`);
			indented(output.slice(-OUTPUT_LINES));
		}
		console.log("");
	}
	if (held)
		console.log(
			dim(`  +${held} more not shown; the full results have every failure.\n`),
		);
};

/**
 * One line per suite, then the counts, then why anything failed. The reason goes last on purpose:
 * it is what you came for, and it should be the thing still on screen when a long run ends.
 */
export const render = (
	runs: SuiteRun[],
	typesRun: TestType[],
	archived?: string,
) => {
	const totals = { passed: 0, failed: 0, skipped: 0 };
	let filtered = 0;

	console.log("");
	for (const testType of TEST_TYPES) {
		// the registry's order, not the order things happened to finish in
		const typeRuns = runs
			.filter((run) => run.testType === testType)
			.sort((a, b) => SUITES.indexOf(a.suite) - SUITES.indexOf(b.suite));
		if (!typeRuns.length) continue;
		console.log(`  ${bold(typeLabel[testType])}`);
		for (const run of typeRuns) {
			const label = run.suite.id.padEnd(15);
			if (!run.outcome) {
				filtered += 1;
				console.log(`    ${dim(`- ${label}filtered out`)}`);
				continue;
			}
			const counts = tally(run.cases);
			totals.passed += counts.passed;
			totals.failed += counts.failed;
			totals.skipped += counts.skipped;
			const parts = [`${counts.passed} passed`];
			if (counts.failed) parts.push(`${counts.failed} failed`);
			if (counts.skipped) parts.push(`${counts.skipped} skipped`);
			const summary =
				run.outcome === "timed out"
					? "timed out"
					: run.note
						? run.note
						: parts.join(", ");
			const ok = run.outcome === "passed";
			console.log(
				`    ${ok ? green("PASS") : red("FAIL")} ${label}${summary.padEnd(30)}${dim(duration(run.seconds))}`,
			);
		}
	}

	const missing = TEST_TYPES.filter((testType) => !typesRun.includes(testType));
	// a suite that died before writing any results has no failing test to be counted, so it has to
	// be said separately or the totals would read green while something was plainly broken
	const brokenSuites = runs.filter(
		(run) => broke(run) && !run.cases.some((item) => item.status === "failed"),
	).length;
	const counted = [
		`${totals.failed} failed`,
		`${totals.passed} passed`,
		totals.skipped ? `${totals.skipped} skipped` : undefined,
		brokenSuites
			? `${brokenSuites} suites did not run to completion`
			: undefined,
		filtered ? `${filtered} suites filtered out` : undefined,
	]
		.filter(Boolean)
		.join(", ");
	console.log(
		`\n${totals.failed || brokenSuites ? red(counted) : green(counted)}.`,
	);
	if (missing.length)
		console.log(
			dim(
				`${missing.map((testType) => typeLabel[testType]).join(" and ")} not run.`,
			),
		);
	if (archived) console.log(dim(`full results: ${archived}`));

	// last, so the reason is the thing still on screen when the run ends rather than a count
	renderFailures(runs);
};
