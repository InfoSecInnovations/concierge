/**
 * An Http built from a table of canned responses.
 *
 * A request to a URL the table does not cover throws with that URL in the message. That is deliberate:
 * it is how a test catches an accidental live call, and it makes the exact URLs and headers the
 * registries are asked for assertable rather than incidental.
 */

import type { Http } from "../http";

export type Answer = {
	status?: number;
	headers?: Record<string, string>;
	body?: unknown;
};

export type Route = [
	string | RegExp,
	Answer | ((url: string, init?: RequestInit) => Answer),
];

export type Asked = { url: string; init?: RequestInit };

export const httpStub = (routes: Route[]) => {
	const asked: Asked[] = [];
	const http: Http = async (url, init) => {
		asked.push({ url, init });
		const route = routes.find(([match]) =>
			typeof match === "string" ? match === url : match.test(url),
		);
		if (!route) throw new Error(`nothing stubbed for ${url}`);
		const answer =
			typeof route[1] === "function" ? route[1](url, init) : route[1];
		return new Response(
			answer.body === undefined ? null : JSON.stringify(answer.body),
			{ status: answer.status ?? 200, headers: answer.headers },
		);
	};
	return {
		http,
		asked,
		headersOf: (index: number) =>
			new Headers(asked[index]?.init?.headers ?? {}),
		urls: () => asked.map(({ url }) => url),
	};
};

/** the shape PyPI's simple JSON API answers with, trimmed to what this tool reads */
export const simple = (
	versions: string[],
	files: { filename: string; yanked?: boolean | string }[] = [],
	extra: Record<string, unknown> = {},
) => ({ name: "x", versions, files, ...extra });

/** the shape npm's abbreviated metadata answers with */
export const abbreviated = (
	versions: Record<string, { deprecated?: string }>,
	distTags: Record<string, string> = {},
) => ({ versions, "dist-tags": distTags });
