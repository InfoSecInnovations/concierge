/**
 * What a container registry has published for a repository.
 *
 * One code path for Docker Hub, Quay and GHCR, because all three implement the OCI distribution API and
 * all three answer an unauthenticated request with the same challenge. The alternative - three bespoke
 * clients - would also be three times the payload: hub.docker.com's own tags endpoint carries digests
 * and per architecture records for every tag, where /v2/.../tags/list carries bare strings, and
 * library/postgres is 1422 of them in about 20 KB.
 *
 * Two behaviours here are not guesses. `n=1000` is always sent because Quay caps a page at 100 whatever
 * you ask and GHCR defaults to 100, so omitting it turns an eleven page crawl into thirty. And a missing
 * or private repository does not answer 404: Docker Hub and Quay answer 401 and GHCR answers 403, so
 * that case is reported as unreadable rather than as deleted.
 */

import type { Client } from "../http";
import { type Candidate, type TagShape, newest } from "../tag";
import type { Catalogue, ImageRef, Release } from "../types";

/** the ref spells it docker.io, the API lives somewhere else, and the token realm somewhere else again */
const HUB_API = "registry-1.docker.io";
const HUB_NAMES = new Set([
	"docker.io",
	"index.docker.io",
	"registry-1.docker.io",
]);

const MANIFEST_ACCEPT = [
	"application/vnd.oci.image.index.v1+json",
	"application/vnd.docker.distribution.manifest.list.v2+json",
	"application/vnd.oci.image.manifest.v1+json",
	"application/vnd.docker.distribution.manifest.v2+json",
].join(", ");

const MAX_PAGES = 50;

/** which host to ask and under what path, applying Docker Hub's implicit library/ namespace */
export const target = (image: Pick<ImageRef, "registry" | "repository">) => {
	const hub = !image.registry || HUB_NAMES.has(image.registry);
	return {
		host: hub ? HUB_API : image.registry,
		repository:
			hub && !image.repository.includes("/")
				? `library/${image.repository}`
				: image.repository,
	};
};

const fields = (header: string) => {
	const found = new Map<string, string>();
	for (const [, key, value] of header.matchAll(/(\w+)="([^"]*)"/g))
		found.set(key as string, value as string);
	return found;
};

/**
 * An anonymous pull token, from the realm the challenge itself names. Deriving the realm rather than
 * hardcoding it is what makes Docker Hub's registry-1/auth split fall out for free.
 */
const tokenFrom = async (
	challenged: Response,
	host: string,
	repository: string,
	client: Client,
) => {
	const header = challenged.headers.get("www-authenticate");
	if (!header) throw new Error(`${host} asked for auth without saying where`);
	const parsed = fields(header);
	const realm = parsed.get("realm");
	if (!realm) throw new Error(`${host} named no token realm`);
	const url = new URL(realm);
	const service = parsed.get("service");
	if (service) url.searchParams.set("service", service);
	url.searchParams.set("scope", `repository:${repository}:pull`);
	const response = await client.request(url.toString());
	if (!response.ok)
		throw new Error(
			`${host} returned ${response.status} issuing a token for ${repository}`,
		);
	const body = (await response.json()) as {
		token?: string;
		access_token?: string;
	};
	const token = body.token ?? body.access_token;
	if (!token)
		throw new Error(`${host} issued an empty token for ${repository}`);
	return token;
};

const authorised = (bearer?: string, accept = "application/json") => ({
	headers: bearer ? { accept, authorization: `Bearer ${bearer}` } : { accept },
});

const nextPage = (response: Response, host: string) => {
	const link = response.headers.get("link");
	const match = link ? /<([^>]+)>\s*;\s*rel="?next"?/.exec(link) : null;
	return match
		? new URL(match[1] as string, `https://${host}`).toString()
		: null;
};

/** every tag the repository has, following the Link header the registry paginates with */
export const tags = async (image: ImageRef, client: Client) => {
	const { host, repository } = target(image);
	let bearer: string | undefined;
	let url: string | null = `https://${host}/v2/${repository}/tags/list?n=1000`;
	const collected: string[] = [];

	for (let page = 0; page < MAX_PAGES && url; page++) {
		let response = await client.request(url, authorised(bearer));
		if (response.status === 401 && !bearer) {
			bearer = await tokenFrom(response, host, repository, client);
			response = await client.request(url, authorised(bearer));
		}
		if (response.status === 401 || response.status === 403)
			throw new Error(
				`${repository} was not found on ${host}, or is not readable anonymously`,
			);
		if (!response.ok)
			throw new Error(`${host} returned ${response.status} for ${repository}`);
		const body = (await response.json()) as { tags?: string[] | null };
		collected.push(...(body.tags ?? []));
		url = nextPage(response, host);
	}
	// a registry that keeps offering another page is a bug or a trap, not a repository with more tags
	if (url)
		throw new Error(
			`${repository} on ${host} has more than ${MAX_PAGES} pages of tags`,
		);
	return { tags: collected, host, repository, bearer };
};

const digestOf = async (
	host: string,
	repository: string,
	tag: string,
	client: Client,
	bearer?: string,
) => {
	const response = await client.request(
		`https://${host}/v2/${repository}/manifests/${encodeURIComponent(tag)}`,
		{ method: "HEAD", ...authorised(bearer, MANIFEST_ACCEPT) },
		host,
	);
	return response.ok ? response.headers.get("docker-content-digest") : null;
};

/**
 * Which concrete tag `latest` is an alias for, when it can be told cheaply. Only the top few candidates
 * are worth asking about, since latest is nearly always one of them, and a miss is reported rather than
 * guessed. These are manifest requests, the ones that count against Docker Hub's anonymous pull limit,
 * which is why the caller can turn the whole thing off.
 */
const resolveLatest = async (
	host: string,
	repository: string,
	candidates: Candidate[],
	client: Client,
	bearer?: string,
) => {
	const wanted = await digestOf(host, repository, "latest", client, bearer);
	if (!wanted) return undefined;
	for (const candidate of candidates.slice(-3).reverse())
		if (
			(await digestOf(host, repository, candidate.tag, client, bearer)) ===
			wanted
		)
			return candidate;
	return undefined;
};

const release = (candidate: Candidate): Release => ({
	// the slot is what `set` takes and what a rewrite substitutes; the tag is the whole reference
	version: candidate.value,
	raw: candidate.tag === candidate.value ? undefined : candidate.tag,
	prerelease: candidate.version?.prerelease ?? false,
});

export const ociCatalogue = async (
	image: ImageRef,
	shape: TagShape,
	client: Client,
	options: { resolveLatest?: boolean } = {},
): Promise<Catalogue> => {
	const listed = await tags(image, client);
	const selection = newest(shape, listed.tags);
	const notes: string[] = [];

	if (shape.label)
		notes.push(
			`held "${shape.label}" constant, so a tag for another variant was not considered`,
		);
	if (selection.how === "label")
		notes.push(
			`the newest plain version is ${selection.stream?.value ?? "unknown"}, which was never published for this variant`,
		);
	if (!selection.latest)
		notes.push("no tag upstream matches the shape of this pin");

	const distTags: Record<string, string> = {};
	if (listed.tags.includes("latest") && options.resolveLatest !== false) {
		const points = await resolveLatest(
			listed.host,
			listed.repository,
			selection.all,
			client,
			listed.bearer,
		);
		if (points) distTags.latest = points.value;
		else notes.push("the latest tag could not be matched to a version tag");
	}

	// mapped once and then selected from, so the catalogue holds one object per release. Building the
	// latest separately produced an equal but distinct one, which every identity based lookup missed
	const releases = selection.all.map(release);
	const listedAs = (candidate?: Candidate) =>
		candidate
			? releases.find(({ version }) => version === candidate.value)
			: undefined;

	return {
		releases,
		latestStable: listedAs(selection.latest),
		latestPrerelease: listedAs(selection.prerelease),
		distTags,
		label: shape.label,
		notes,
	};
};
