/**
 * Works out which components have changed since their baseline, bumps those, rewrites every reference
 * to the versions it moved, and refuses to release a version number that has already been published.
 *
 * bun run ./versioning/bump.ts --release-type <alpha|rc|latest> --importance <major|minor|patch>
 *   [--scope shabti|launcher]  which workflow is releasing: shabti releases everything except the
 *                              configurator, launcher releases the configurator
 *   [--dry-run]                work out and report the versions without writing anything
 *   [--force]                  release even though nothing has changed
 *   [--allow-dirty]            skip the uncommitted changes check
 *   [--no-docker-check]        skip the Docker Hub tag collision check
 */

import { parseArgs } from "node:util";
import semver from "semver";
import { pathsChanged, resolveBaseline, type Baseline } from "./diffGit";
import { comparePyPi } from "./diffPypi";
import { isPublished } from "./published";
import { EditPlan, readRef } from "./refs";
import {
	type Component,
	type Scope,
	inScope,
	releaseCommitMessage,
	releaseTag,
	topoSort,
} from "./registry";
import {
	type BumpReport,
	type ComponentReport,
	type Reason,
	publishReport,
} from "./report";
import { git, isDirty, run } from "./repo";
import {
	IMPORTANCES,
	RELEASE_TYPES,
	computeVersion,
	npmDistTag,
} from "./versions";

const { values } = parseArgs({
	args: Bun.argv.slice(2),
	options: {
		"release-type": { type: "string" },
		importance: { type: "string" },
		scope: { type: "string", default: "shabti" },
		"dry-run": { type: "boolean", default: false },
		force: { type: "boolean", default: false },
		"allow-dirty": { type: "boolean", default: false },
		"no-docker-check": { type: "boolean", default: false },
	},
});

const oneOf = <T extends string>(
	name: string,
	value: unknown,
	allowed: T[],
) => {
	if (!allowed.includes(value as T))
		throw new Error(
			`--${name} must be one of ${allowed.join(", ")}, got ${value ?? "nothing"}`,
		);
	return value as T;
};

const releaseType = oneOf(
	"release-type",
	values["release-type"],
	RELEASE_TYPES,
);
const importance = oneOf("importance", values.importance, IMPORTANCES);
const scope = oneOf<Scope>("scope", values.scope, ["shabti", "launcher"]);
const dryRun = !!values["dry-run"];

interface Detection {
	changed: boolean;
	reason: Reason;
	baseline: string;
	warning?: string;
}

const detect = async (
	component: Component,
	currentVersion: string,
	baseline: Baseline,
): Promise<Detection> => {
	switch (component.probe.kind) {
		case "always":
			return { changed: true, reason: "release", baseline: "none" };
		case "pypiSdist": {
			if (component.registry.kind !== "pypi")
				throw new Error(
					`${component.id} has no PyPI package to compare against`,
				);
			const comparison = await comparePyPi(
				component.registry.name,
				component.dir,
				currentVersion,
			);
			return {
				changed: comparison.changed,
				reason: comparison.reason,
				baseline: `pypi:${currentVersion}`,
				warning: comparison.warning,
			};
		}
		case "git": {
			if (!baseline.tag)
				return { changed: true, reason: "noBaseline", baseline: "none" };
			const changed = await pathsChanged(baseline.tag, component.probe.paths);
			return {
				changed,
				reason: changed ? "intrinsic" : "unchanged",
				baseline: `git:${baseline.tag}`,
			};
		}
	}
};

const main = async () => {
	if (!values["allow-dirty"] && (await isDirty()))
		throw new Error(
			"the working tree has uncommitted changes, which would end up in the release: commit them, or pass --allow-dirty",
		);

	const components = inScope(scope);
	const { sorted, graph } = topoSort(components);
	const warnings: string[] = [];

	const currentVersions = new Map<string, string>();
	for (const component of components) {
		const version = await readRef(component.source);
		if (!semver.valid(version))
			throw new Error(
				`${component.source.file} declares ${version}, which is not a valid semver version`,
			);
		currentVersions.set(component.id, version);
	}

	const root = components.find(
		(component) => component.id === "root",
	) as Component;
	const rootVersion = currentVersions.get(root.id) as string;
	const baseline = await resolveBaseline(rootVersion);
	if (baseline.warning) warnings.push(baseline.warning);

	const asReport = (
		component: Component,
		newVersion: string,
		reason: Reason,
		options?: { changed?: boolean; baseline?: string; triggers?: string[] },
	): ComponentReport => ({
		id: component.id,
		label: component.label,
		registry: component.registry.kind,
		currentVersion: currentVersions.get(component.id) as string,
		newVersion,
		changed:
			options?.changed ?? newVersion !== currentVersions.get(component.id),
		reason,
		baseline: options?.baseline ?? "none",
		dependencyTriggers: options?.triggers ?? [],
	});

	const finish = async (
		reports: ComponentReport[],
		touchedFiles: string[],
		bumped: boolean,
	) => {
		const shabtiVersion = reports.find((report) => report.id === root.id)
			?.newVersion as string;
		const report: BumpReport = {
			releaseType,
			importance,
			scope,
			dryRun,
			bumped,
			baselineTag: baseline.tag,
			shabtiVersion,
			releaseTag: releaseTag(shabtiVersion),
			commitMessage: releaseCommitMessage(shabtiVersion),
			prerelease: !!semver.prerelease(shabtiVersion)?.length,
			npmDistTag: npmDistTag(
				reports.find((entry) => entry.id === "shabtiApiClientNode")
					?.newVersion ?? shabtiVersion,
			),
			components: reports,
			touchedFiles,
			warnings,
		};
		await publishReport(report);
	};

	// a release that got as far as pushing its version bump but died before the release itself: the
	// versions are already correct, so republish them rather than bumping a second time
	const lastCommit = (await git("log", "-1", "--pretty=%s")).stdout.trim();
	if (
		lastCommit === releaseCommitMessage(rootVersion) &&
		!(await isPublished(root, rootVersion)).published
	) {
		warnings.push(
			`resuming the pending release of ${releaseTag(rootVersion)}: versions are already bumped`,
		);
		await finish(
			sorted.map((component) =>
				asReport(
					component,
					currentVersions.get(component.id) as string,
					"pending",
					{ changed: false },
				),
			),
			[],
			false,
		);
		return;
	}

	const detections = new Map(
		await Promise.all(
			components.map(
				async (component) =>
					[
						component.id,
						await detect(
							component,
							currentVersions.get(component.id) as string,
							baseline,
						),
					] as const,
			),
		),
	);
	for (const detection of detections.values())
		if (detection.warning) warnings.push(detection.warning);

	const reports: ComponentReport[] = [];
	const byId = new Map<string, ComponentReport>();
	for (const component of sorted) {
		const currentVersion = currentVersions.get(component.id) as string;
		const detection = detections.get(component.id) as Detection;
		const triggers = (graph.get(component.id) ?? []).filter((id) => {
			const dependency = byId.get(id);
			return (
				!!dependency && dependency.newVersion !== dependency.currentVersion
			);
		});
		const changed = detection.changed || triggers.length > 0;
		const newVersion = computeVersion(
			currentVersion,
			releaseType,
			importance,
			changed,
		);
		const reason: Reason = changed
			? detection.changed
				? detection.reason
				: "dependency"
			: newVersion === currentVersion
				? detection.reason
				: "prereleaseStrip";
		const report = asReport(component, newVersion, reason, {
			changed,
			baseline: detection.baseline,
			triggers,
		});
		byId.set(component.id, report);
		reports.push(report);
	}

	// promoting a release candidate is a release in its own right even when no component changed
	const promoting =
		releaseType === "latest" && !!semver.prerelease(rootVersion)?.length;
	const moved = reports.filter(
		(report) =>
			report.id !== root.id && report.newVersion !== report.currentVersion,
	);
	if (!moved.length && !promoting && !values.force)
		throw new Error(
			`nothing has changed since ${baseline.tag ?? "the last release"}, so there is nothing to release: pass --force to release anyway`,
		);

	const collisions: string[] = [];
	await Promise.all(
		reports
			.filter((report) => report.newVersion !== report.currentVersion)
			.map(async (report) => {
				const component = components.find(
					(entry) => entry.id === report.id,
				) as Component;
				const check = await isPublished(component, report.newVersion, {
					checkDocker: !values["no-docker-check"],
				});
				if (check.warning) warnings.push(check.warning);
				if (check.published)
					collisions.push(
						`${component.label} ${report.newVersion} (${component.registry.kind})`,
					);
			}),
	);
	if (collisions.length)
		throw new Error(
			`these versions have already been published, so this release would overwrite or silently skip them:\n  ${collisions.join("\n  ")}\nthe versions declared in this branch are probably out of date.`,
		);

	const plan = new EditPlan();
	for (const component of sorted) {
		const report = byId.get(component.id) as ComponentReport;
		if (report.newVersion === report.currentVersion) continue;
		for (const ref of component.refs)
			await plan.edit(ref, report.currentVersion, report.newVersion);
	}

	const touchedFiles = plan.files;
	if (touchedFiles.length) {
		if (!dryRun) {
			await plan.write();
			// the workspace package versions live in bun.lock, and shabti-components.json is what the
			// configurator reads to decide which image tags to pull
			await run(["bun", "install", "--lockfile-only"]);
			await run(["bun", "./generateComponentsJson.ts"]);
		}
		touchedFiles.push("bun.lock", "shabti-components.json");
	}

	await finish(reports, touchedFiles, !dryRun && touchedFiles.length > 0);
};

try {
	await main();
} catch (err) {
	console.error(`\n${err instanceof Error ? err.message : err}\n`);
	process.exit(1);
}
