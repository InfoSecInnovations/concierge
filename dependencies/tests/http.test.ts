import { describe, expect, test } from "bun:test";
import { type Http, client } from "../http";

/** an Http that records what it was asked for and answers from a table */
const stub = (
	answers: Record<string, Response | (() => Response | Promise<Response>)>,
) => {
	const asked: string[] = [];
	const http: Http = async (url) => {
		asked.push(url);
		const answer = answers[url];
		if (!answer) throw new Error(`nothing stubbed for ${url}`);
		return typeof answer === "function" ? await answer() : answer.clone();
	};
	return { http, asked };
};

const ok = (body = "{}") => new Response(body, { status: 200 });

/** collects the sleeps rather than performing them, so a retry test costs nothing */
const clock = () => {
	const slept: number[] = [];
	return {
		slept,
		sleep: async (ms: number) => {
			slept.push(ms);
		},
		now: () => 1_000_000,
	};
};

describe("once", () => {
	test("computes a key once however many callers ask", async () => {
		const deps = client();
		let calls = 0;
		const task = async () => {
			calls++;
			return "answer";
		};
		const [first, second, third] = await Promise.all([
			deps.once("k", task),
			deps.once("k", task),
			deps.once("k", task),
		]);
		expect([first, second, third]).toEqual(["answer", "answer", "answer"]);
		expect(calls).toBe(1);
	});

	test("keeps different keys apart", async () => {
		const deps = client();
		expect(await deps.once("a", async () => 1)).toBe(1);
		expect(await deps.once("b", async () => 2)).toBe(2);
	});

	test("shares a memo passed in, so a caller can span two clients", async () => {
		const memo = new Map<string, Promise<unknown>>();
		let calls = 0;
		const task = async () => {
			calls++;
			return "answer";
		};
		await client({ memo }).once("k", task);
		await client({ memo }).once("k", task);
		expect(calls).toBe(1);
	});
});

describe("retry", () => {
	test("retries a 429 and honours Retry-After", async () => {
		let calls = 0;
		const { http } = stub({
			"https://x/a": () => {
				calls++;
				return calls === 1
					? new Response("", { status: 429, headers: { "retry-after": "7" } })
					: ok();
			},
		});
		const time = clock();
		const response = await client({ http, ...time }).request("https://x/a");
		expect(response.status).toBe(200);
		expect(calls).toBe(2);
		expect(time.slept).toEqual([7000]);
	});

	test("retries a 5xx with the backoff when no Retry-After is given", async () => {
		let calls = 0;
		const { http } = stub({
			"https://x/b": () => {
				calls++;
				return calls < 3 ? new Response("", { status: 503 }) : ok();
			},
		});
		const time = clock();
		expect(
			(await client({ http, ...time }).request("https://x/b")).status,
		).toBe(200);
		expect(calls).toBe(3);
		expect(time.slept).toHaveLength(2);
		expect(time.slept[0]).toBeLessThan(time.slept[1] as number);
	});

	test("retries a network error and rethrows it when it never clears", async () => {
		const http: Http = async () => {
			throw new Error("econnreset");
		};
		const time = clock();
		await expect(
			client({ http, ...time }).request("https://x/c"),
		).rejects.toThrow(/econnreset/);
		// the first attempt plus every retry
		expect(time.slept).toHaveLength(2);
	});

	test("never retries a 4xx that is not a 429", async () => {
		let calls = 0;
		const { http } = stub({
			"https://x/d": () => {
				calls++;
				return new Response("", { status: 403 });
			},
		});
		const time = clock();
		expect(
			(await client({ http, ...time }).request("https://x/d")).status,
		).toBe(403);
		expect(calls).toBe(1);
		expect(time.slept).toEqual([]);
	});

	test("gives back the last response when the retries run out", async () => {
		const { http } = stub({
			"https://x/e": () => new Response("", { status: 429 }),
		});
		const time = clock();
		expect(
			(await client({ http, ...time }).request("https://x/e")).status,
		).toBe(429);
	});

	test("does not retry at all when told not to", async () => {
		let calls = 0;
		const { http } = stub({
			"https://x/f": () => {
				calls++;
				return new Response("", { status: 500 });
			},
		});
		await client({ http, retries: 0, ...clock() }).request("https://x/f");
		expect(calls).toBe(1);
	});
});

describe("limits", () => {
	/** an Http that never settles until released, so overlap is observable */
	const held = () => {
		let live = 0;
		let peak = 0;
		const releases: (() => void)[] = [];
		const http: Http = async () => {
			live++;
			peak = Math.max(peak, live);
			await new Promise<void>((resolve) => releases.push(resolve));
			live--;
			return ok();
		};
		return {
			http,
			get peak() {
				return peak;
			},
			releaseAll: () => {
				while (releases.length) releases.shift()?.();
			},
		};
	};

	test("never exceeds the concurrency limit", async () => {
		const gate = held();
		const deps = client({ http: gate.http, concurrency: 2 });
		const all = Promise.all(
			Array.from({ length: 6 }, (_, index) =>
				deps.request(`https://x/${index}`),
			),
		);
		// let the first batch reach the stub, then let everything drain
		await Bun.sleep(0);
		expect(gate.peak).toBe(2);
		const drain = setInterval(() => gate.releaseAll(), 0);
		await all;
		clearInterval(drain);
		expect(gate.peak).toBe(2);
	});

	test("serialises requests sharing a host and lets other hosts through", async () => {
		const gate = held();
		const deps = client({ http: gate.http, concurrency: 6 });
		const all = Promise.all([
			deps.request("https://a/1", undefined, "a"),
			deps.request("https://a/2", undefined, "a"),
			deps.request("https://a/3", undefined, "a"),
			deps.request("https://b/1", undefined, "b"),
			deps.request("https://c/1", undefined, "c"),
		]);
		await Bun.sleep(0);
		// one per serialised host, never two of the same
		expect(gate.peak).toBe(3);
		const drain = setInterval(() => gate.releaseAll(), 0);
		await all;
		clearInterval(drain);
		expect(gate.peak).toBe(3);
	});

	test("one failing request does not poison the rest of its host's chain", async () => {
		let calls = 0;
		const http: Http = async () => {
			calls++;
			if (calls === 1) throw new Error("first fails");
			return ok();
		};
		const deps = client({ http, retries: 0, ...clock() });
		const first = deps.request("https://a/1", undefined, "a");
		const second = deps.request("https://a/2", undefined, "a");
		await expect(first).rejects.toThrow(/first fails/);
		expect((await second).status).toBe(200);
	});
});
