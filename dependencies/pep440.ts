/**
 * PEP 440 versions: parsing, normalising and ordering.
 *
 * versioning/versions.ts already reads PEP 440, but only the narrow shape our own packages are allowed
 * to use, and it bridges to semver to compare. Neither works here. Third party versions include four
 * release segments (apache/tika 3.3.0.0), one segment (shiny 0.1), post and dev releases and epochs,
 * none of which semver can represent - and semver actively misorders what it can parse, since PEP 440
 * puts 1.0.post1 above 1.0 while any semver reading of 1.0.0-post.1 puts it below. So this is a
 * separate, permissive implementation, and semver stays for npm alone.
 */

/** the pre-release stages as PEP 440 spells them once normalised */
const PRE_LETTERS = {
	alpha: "a",
	a: "a",
	beta: "b",
	b: "b",
	c: "rc",
	pre: "rc",
	preview: "rc",
	rc: "rc",
} as const;

export type PreLetter = "a" | "b" | "rc";

export type Version = {
	epoch: number;
	/** the release segments, zero padding stripped from each, as parsed */
	release: number[];
	pre?: { letter: PreLetter; number: number };
	post?: number;
	dev?: number;
	/** normalised: lower case, separators folded to "." */
	local?: string;
	/** a pre-release or a dev release. A post-release of a pre-release is still one */
	prerelease: boolean;
	/** the normalised spelling, which is what a manifest should be written with */
	canonical: string;
};

/**
 * packaging's VERSION_PATTERN, transcribed rather than reinvented. Assembled from strings because
 * JavaScript has no extended-regex flag and this needs the comments.
 *
 * Every branch earns its keep: the bare `-N` post alternative is what makes apache/tika's 4.0.0-1
 * readable, and the optional pre, post and dev counters are what make 1.2a and 1.0.post legal. Each
 * part is wrapped in a group of its own, because an absent counter is an implicit zero and so the
 * counter cannot tell presence from absence.
 */
const VERSION = new RegExp(
	[
		"^v?",
		"(?:(?<epoch>[0-9]+)!)?",
		"(?<release>[0-9]+(?:\\.[0-9]+)*)",
		"(?<pre>[-_.]?(?<preL>alpha|a|beta|b|preview|pre|c|rc)[-_.]?(?<preN>[0-9]+)?)?",
		"(?<post>(?:-(?<postN1>[0-9]+))|(?:[-_.]?(?:post|rev|r)[-_.]?(?<postN2>[0-9]+)?))?",
		"(?<dev>[-_.]?dev[-_.]?(?<devN>[0-9]+)?)?",
		"(?:\\+(?<local>[a-z0-9]+(?:[-_.][a-z0-9]+)*))?$",
	].join(""),
	"i",
);

const canonicalOf = (version: Omit<Version, "prerelease" | "canonical">) =>
	[
		version.epoch ? `${version.epoch}!` : "",
		version.release.join("."),
		version.pre ? `${version.pre.letter}${version.pre.number}` : "",
		version.post === undefined ? "" : `.post${version.post}`,
		version.dev === undefined ? "" : `.dev${version.dev}`,
		version.local ? `+${version.local}` : "",
	].join("");

/**
 * A version, or null when it is not PEP 440 at all. Null rather than a throw because every caller wants
 * something different from an unreadable version: a registry listing drops it and counts it, a pin
 * reports it, and only a version a user asked us to write is worth refusing over.
 *
 * There is deliberately no legacy fallback. packaging dropped LegacyVersion too, and guessing an order
 * for `2.0-SNAPSHOT` would be worse than admitting we cannot read it.
 */
export const parse = (text: string): Version | null => {
	const groups = VERSION.exec(text.trim())?.groups;
	if (!groups) return null;

	// zero padding is not significant anywhere in PEP 440, so Number() is the normalisation
	const parsed = {
		epoch: groups.epoch ? Number(groups.epoch) : 0,
		release: (groups.release as string).split(".").map(Number),
		pre: groups.pre
			? {
					letter:
						PRE_LETTERS[
							(groups.preL as string).toLowerCase() as keyof typeof PRE_LETTERS
						],
					number: groups.preN ? Number(groups.preN) : 0,
				}
			: undefined,
		// `1.0-1` is a post release, spelled the way a Debian revision would be
		post: groups.post ? Number(groups.postN1 ?? groups.postN2 ?? 0) : undefined,
		dev: groups.dev ? Number(groups.devN ?? 0) : undefined,
		local: groups.local?.toLowerCase().replace(/[-_.]+/g, "."),
	};

	return {
		...parsed,
		prerelease: !!parsed.pre || parsed.dev !== undefined,
		canonical: canonicalOf(parsed),
	};
};

/** the same version, spelled the way PEP 440 says it should be, or null when it is not a version */
export const canonical = (text: string) => parse(text)?.canonical ?? null;

type Atom = number | string | Atom[];

/**
 * An absent pre, post, dev or local segment is an infinity rather than a value, which is what makes
 * 1.0.dev1 sort below 1.0a1 and 1.0 sort above both. Comparing one against a present segment therefore
 * compares a number against a tuple, and only its sign matters.
 */
const compareAtom = (a: Atom, b: Atom): number => {
	if (Array.isArray(a) && Array.isArray(b)) {
		for (let index = 0; index < Math.min(a.length, b.length); index++) {
			const order = compareAtom(a[index] as Atom, b[index] as Atom);
			if (order !== 0) return order;
		}
		// a shorter tuple that is otherwise equal is the lower one, e.g. 1.0 below 1.0.1
		return a.length - b.length;
	}
	if (Array.isArray(a)) return b === Number.POSITIVE_INFINITY ? -1 : 1;
	if (Array.isArray(b)) return a === Number.POSITIVE_INFINITY ? 1 : -1;
	if (a === b) return 0;
	return a < b ? -1 : 1;
};

/**
 * Trailing zeros are not significant, so 3.3.0.0 and 3.3 are the same version. Stripping them makes
 * the element-wise comparison fall through to the length, which is what zero padding would have done.
 */
const significant = (release: number[]) => {
	const segments = [...release];
	while (segments.length > 1 && segments[segments.length - 1] === 0)
		segments.pop();
	return segments;
};

/** the six parts PEP 440 orders by, most significant first */
const key = (version: Version): Atom[] => [
	version.epoch,
	significant(version.release),
	version.pre
		? [version.pre.letter, version.pre.number]
		: // a dev release with no pre-release and no post-release sorts below every pre-release of it
			version.dev !== undefined && version.post === undefined
			? Number.NEGATIVE_INFINITY
			: Number.POSITIVE_INFINITY,
	version.post ?? Number.NEGATIVE_INFINITY,
	version.dev ?? Number.POSITIVE_INFINITY,
	version.local
		? // a numeric local segment sorts above an alphabetic one, the least intuitive rule in PEP 440
			version.local
				.split(".")
				.map(
					(segment): Atom =>
						/^[0-9]+$/.test(segment)
							? [Number(segment), ""]
							: [Number.NEGATIVE_INFINITY, segment],
				)
		: Number.NEGATIVE_INFINITY,
];

/** negative when a is the lower version, zero when they are the same version */
export const compare = (a: Version, b: Version) => compareAtom(key(a), key(b));

/**
 * The highest of some versions, or undefined when there are none. Ties break toward more release
 * segments, so a concrete 19.0 wins over a floating docker tag 19, which PEP 440 calls its equal.
 */
export const highest = (versions: Version[]) =>
	versions.reduce<Version | undefined>((best, version) => {
		if (!best) return version;
		const order = compare(version, best);
		if (order > 0) return version;
		if (order === 0 && version.release.length > best.release.length)
			return version;
		return best;
	}, undefined);
