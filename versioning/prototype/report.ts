import fs from "node:fs/promises";
import path from "node:path";
import type { Importance, ReleaseType } from "./versions";

export type Reason =
	| "intrinsic"
	| "dependency"
	| "prereleaseStrip"
	| "unchanged"
	| "release"
	| "pending"
	| "firstPublish"
	| "declaredVersionUnpublished"
	| "noSdist"
	| "noBaseline";

const REASONS: Record<Reason, string> = {
	intrinsic: "changed since its baseline",
	dependency: "a pinned dependency moved",
	prereleaseStrip: "unchanged, promoted to a final release",
	unchanged: "unchanged",
	release: "every release moves this version",
	pending: "already bumped, waiting to be published",
	firstPublish: "never published, releasing as is",
	declaredVersionUnpublished: "declared version not published yet",
	noSdist: "published without an sdist, cannot compare",
	noBaseline: "no baseline to compare against",
};

export interface ComponentReport {
	id: string;
	label: string;
	registry: string;
	currentVersion: string;
	newVersion: string;
	changed: boolean;
	reason: Reason;
	baseline: string;
	dependencyTriggers: string[];
}

export interface BumpReport {
	releaseType: ReleaseType;
	importance: Importance;
	scope: string;
	dryRun: boolean;
	/** whether any version was rewritten, i.e. whether there is anything to commit */
	bumped: boolean;
	baselineTag?: string;
	shabtiVersion: string;
	releaseTag: string;
	commitMessage: string;
	prerelease: boolean;
	npmDistTag: string;
	components: ComponentReport[];
	touchedFiles: string[];
	warnings: string[];
}

const cell = (value: string, width: number) => value.padEnd(width);

const table = (report: BumpReport) => {
	const rows = report.components.map((component) => [
		component.label,
		component.currentVersion,
		component.newVersion === component.currentVersion
			? "-"
			: component.newVersion,
		REASONS[component.reason] +
			(component.dependencyTriggers.length
				? ` (${component.dependencyTriggers.join(", ")})`
				: ""),
		component.baseline,
	]);
	const headers = ["component", "current", "new", "why", "baseline"];
	const widths = headers.map((header, column) =>
		Math.max(header.length, ...rows.map((row) => row[column].length)),
	);
	return [headers, ...rows].map((row) =>
		row.map((value, column) => cell(value, widths[column])).join("  "),
	);
};

export const printReport = (report: BumpReport) => {
	console.log(
		`\n${report.dryRun ? "Would release" : "Releasing"} ${report.releaseTag} (${report.releaseType}, ${report.importance})\n`,
	);
	for (const line of table(report)) console.log(`  ${line}`);
	if (report.touchedFiles.length) {
		console.log(`\n${report.dryRun ? "Would update" : "Updated"}:`);
		for (const file of report.touchedFiles) console.log(`  ${file}`);
	}
	if (report.warnings.length) {
		console.log("\nWarnings:");
		for (const warning of report.warnings) console.log(`  ! ${warning}`);
	}
	console.log("");
};

const DELIMITER = "SHABTI_VERSIONING_EOF";

const setOutputs = async (outputs: Record<string, string>) => {
	const file = process.env.GITHUB_OUTPUT;
	if (!file) return;
	const lines = Object.entries(outputs).map(([key, value]) =>
		value.includes("\n")
			? `${key}<<${DELIMITER}\n${value}\n${DELIMITER}`
			: `${key}=${value}`,
	);
	await fs.appendFile(file, `${lines.join("\n")}\n`);
};

const markdown = (report: BumpReport) =>
	[
		`## ${report.dryRun ? "Version bump (dry run)" : "Version bump"}: ${report.releaseTag}`,
		"",
		`\`${report.releaseType}\` / \`${report.importance}\` release, baseline \`${report.baselineTag ?? "none"}\``,
		"",
		"| Component | Current | New | Why | Baseline |",
		"| --- | --- | --- | --- | --- |",
		...report.components.map(
			(component) =>
				`| ${component.label} | \`${component.currentVersion}\` | ${
					component.newVersion === component.currentVersion
						? "-"
						: `\`${component.newVersion}\``
				} | ${REASONS[component.reason]}${
					component.dependencyTriggers.length
						? ` (${component.dependencyTriggers.join(", ")})`
						: ""
				} | ${component.baseline} |`,
		),
		...(report.warnings.length
			? [
					"",
					"### Warnings",
					...report.warnings.map((warning) => `- ${warning}`),
				]
			: []),
		"",
	].join("\n");

/**
 * Feeds the rest of the workflow: the docker tags, the release tag, the commit message and the exact
 * list of files to stage. The full report is written to the runner's temp directory rather than into
 * the repository, which would dirty the tree the next run diffs against.
 */
export const publishReport = async (report: BumpReport) => {
	printReport(report);
	const summary = process.env.GITHUB_STEP_SUMMARY;
	if (summary) await fs.appendFile(summary, markdown(report));
	const temp = process.env.RUNNER_TEMP;
	if (temp)
		await Bun.write(
			path.join(temp, "version-bump.json"),
			JSON.stringify(report, undefined, "\t"),
		);
	const version = (id: string) =>
		report.components.find((component) => component.id === id)?.newVersion ??
		"";
	await setOutputs({
		bumped: String(report.bumped),
		"shabti-version": report.shabtiVersion,
		"release-tag": report.releaseTag,
		// the release this one follows, which is also where the executables built by the other publish
		// workflow are carried forward from
		"previous-release-tag": report.baselineTag ?? "",
		"commit-message": report.commitMessage,
		"api-version": version("shabtiApi"),
		"web-version": version("shabtiWeb"),
		"node-client-version": version("shabtiApiClientNode"),
		"cli-version": version("shabtiCli"),
		"configurator-version": version("configurator"),
		prerelease: String(report.prerelease),
		"npm-dist-tag": report.npmDistTag,
		"changed-components": report.components
			.filter((component) => component.newVersion !== component.currentVersion)
			.map((component) => component.id)
			.join(","),
		"touched-files": report.touchedFiles.join("\n"),
	});
};
