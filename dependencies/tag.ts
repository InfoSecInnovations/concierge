/**
 * Comparing container image tags, which are not versions and not semver.
 *
 * A tag is a template with one varying slot: `0.11.1-python3.14-trixie-slim` varies the version and
 * holds the base image constant, `server-cuda-b9843` varies a build counter and holds the build variant
 * constant. The pin tells us which template we are on, and the job is to find newer tags on the same
 * one - and to say plainly when there is no template to find.
 *
 * The label is held constant deliberately. It means a newer Python base or an -alpine variant is not
 * searched, so every answer states what it held, rather than quietly implying it looked everywhere.
 */

import { escape } from "../versioning/write";
import { type Version, compare, highest, parse } from "./pep440";

/** how the varying part of a tag is read */
export type Slot = "version" | "build";

export type TagShape = {
	/** literal text before the slot, e.g. "server-cuda-" */
	prefix: string;
	/** literal text after it, held constant: "-full", "-python3.14-trixie-slim", or "" */
	label: string;
	slot: Slot;
	/** the slot as written: "0.11.1", "3.3.0.0", "b9843" */
	value: string;
};

/** one upstream tag that fits a shape */
export type Candidate = {
	/** the whole tag, which is what would be written */
	tag: string;
	/** the slot text as written, so a sibling tag can be constructed from it */
	value: string;
	version?: Version;
	build?: number;
};

const VERSION_SEGMENT = /^v?\d+(?:\.\d+)*$/;
const BUILD_SEGMENT = /^b\d+$/;

/** a Maven style snapshot is a development build, which is what PEP 440 calls a dev release */
const asVersion = (text: string) =>
	parse(text.replace(/[-_.]snapshot$/i, ".dev0"));

/**
 * The template a pinned tag is on, or null when it names no version at all - `latest`, `nightly`, a
 * bare digest. Those are refused rather than guessed at.
 */
export const shapeOf = (tag: string): TagShape | null => {
	// the common case: the whole tag is a version, prereleases and post releases included
	if (asVersion(tag))
		return { prefix: "", label: "", slot: "version", value: tag };

	const segments = tag.split("-");
	for (const [index, segment] of segments.entries()) {
		const slot: Slot | null = VERSION_SEGMENT.test(segment)
			? "version"
			: BUILD_SEGMENT.test(segment)
				? "build"
				: null;
		if (!slot) continue;
		const before = segments.slice(0, index);
		const after = segments.slice(index + 1);
		return {
			prefix: before.length ? `${before.join("-")}-` : "",
			label: after.length ? `-${after.join("-")}` : "",
			slot,
			value: segment,
		};
	}
	return null;
};

/**
 * Every tag fitting one template. The slot pattern is deliberately loose and anchored by the literal
 * label instead: requiring a leading digit is what rejects the `sha-0649641-python3.14-trixie-slim`
 * decoys, and PEP 440 rejecting the rest is what turns `latest`, `trixie`, `18-alpine` and
 * `18.3-alpine3.22` away without a list of exceptions.
 */
export const matching = (
	tags: string[],
	prefix: string,
	label: string,
	slot: Slot,
): Candidate[] => {
	const pattern = new RegExp(
		`^${escape(prefix)}(${
			slot === "build" ? "b[0-9]+" : "[0-9][A-Za-z0-9.!+_-]*"
		})${escape(label)}$`,
	);
	return tags
		.flatMap((tag) => {
			const value = pattern.exec(tag)?.[1];
			if (value === undefined) return [];
			if (slot === "build")
				return [{ tag, value, build: Number(value.slice(1)) }];
			const version = asVersion(value);
			return version ? [{ tag, value, version }] : [];
		})
		.sort(order);
};

/** ascending, tie broken toward the more precise tag so a floating `19` never beats a concrete `19.0` */
const order = (a: Candidate, b: Candidate) => {
	if (a.build !== undefined && b.build !== undefined) return a.build - b.build;
	if (!a.version || !b.version) return 0;
	const versions = compare(a.version, b.version);
	return versions !== 0
		? versions
		: a.version.release.length - b.version.release.length;
};

const top = (candidates: Candidate[], stable: boolean) => {
	const eligible = stable
		? candidates.filter((candidate) => !candidate.version?.prerelease)
		: candidates;
	if (!eligible.length) return undefined;
	// highest() already breaks a tie toward more release segments; builds are plain integers
	if (eligible[0]?.build !== undefined) return eligible[eligible.length - 1];
	const best = highest(
		eligible.flatMap((candidate) =>
			candidate.version ? [candidate.version] : [],
		),
	);
	return eligible.find((candidate) => candidate.version === best);
};

export type Selection = {
	/** the newest tag on the pin's template, when there is one */
	latest?: Candidate;
	/** the newest prerelease on it, when one sorts above `latest` */
	prerelease?: Candidate;
	/** the newest pure version tag, i.e. the version stream the label variants follow */
	stream?: Candidate;
	/** how `latest` was reached, so the report can explain itself */
	how: "stream" | "label" | "build" | "none";
	/** every candidate on the pin's template, ascending */
	all: Candidate[];
};

/**
 * The newest tag to move a pin to.
 *
 * Resolved through the unlabelled version stream rather than by comparing labelled tags directly. The
 * reason is apache/tika: pinned at `3.3.0.0-full`, the labelled tags alone make `3.3.1.0-full` look
 * like the answer, because `4.0.0-full` has three release segments where the pin has four and sorts
 * ambiguously against it. Asking the stream first - what is the newest plain version? - gives `4.0.0`,
 * and `4.0.0-full` exists, so the real major is found without any rule about segment counts.
 */
export const newest = (shape: TagShape, tags: string[]): Selection => {
	if (shape.slot === "build") {
		const all = matching(tags, shape.prefix, shape.label, "build");
		return { latest: top(all, false), how: all.length ? "build" : "none", all };
	}

	const all = matching(tags, shape.prefix, shape.label, "version");
	const prerelease = top(
		all.filter((candidate) => candidate.version?.prerelease),
		false,
	);
	const withPrerelease = (selection: Omit<Selection, "all" | "prerelease">) => {
		const ahead =
			prerelease &&
			(!selection.latest || order(prerelease, selection.latest) > 0)
				? prerelease
				: undefined;
		return { ...selection, prerelease: ahead, all };
	};

	// an unlabelled pin is already on the stream, so there is nothing to reconcile
	if (!shape.label) {
		const only = top(all, true);
		return withPrerelease({
			latest: only,
			stream: only,
			how: only ? "stream" : "none",
		});
	}

	const stream = top(matching(tags, shape.prefix, "", "version"), true);
	const onStream =
		stream &&
		all.find(
			(candidate) =>
				candidate.tag === `${shape.prefix}${stream.value}${shape.label}`,
		);
	const labelled = top(all, true);
	// the stream's answer, unless a labelled tag somehow sits above it, which can only be an improvement
	const latest =
		onStream && (!labelled || order(labelled, onStream) <= 0)
			? onStream
			: labelled;
	return withPrerelease({
		latest,
		stream,
		how: latest && latest === onStream ? "stream" : latest ? "label" : "none",
	});
};
