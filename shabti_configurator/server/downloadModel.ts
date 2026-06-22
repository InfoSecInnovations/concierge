import { HTTPException } from "hono/http-exception";
import { sleep } from "bun";
import getModelsConfig from "./getModelsConfig";
import { createEventSource } from "eventsource-client";

const TIMEOUT = 10000;
const HEALTH_POLL_INTERVAL = 300;

export default async function* (modelName: string) {
	// TODO: hit llama.cpp API instead
	const shabtiModels = await getModelsConfig();
	const modelData = shabtiModels[modelName];
	if (!modelData) throw new HTTPException(404, { message: "model not found" });
	const start = performance.now();
	while (performance.now() - start < TIMEOUT) {
		try {
			if (
				await fetch("http://localhost:11434/v1/health").then(
					(res) => res.status == 200,
				)
			)
				break;
		} catch {}
		sleep(HEALTH_POLL_INTERVAL);
	}
	// TODO: this must be the actual repo instead of modelName
	const res = await fetch("http://localhost:11434/models/", {
		body: JSON.stringify({ model: modelName }),
		method: "POST",
	});
	if (res.status != 200) {
		const json = (await res.json()) as any;
		console.log(json.error.error);
		// TODO: capture whether this is actually because the model is already downloaded or another reason
		throw new HTTPException(500, { message: json.error.error });
	}
	const eventSource = createEventSource("http://localhost:11434/models/sse");
	for await (const { data, event, model } of eventSource) {
		console.log(data);
		console.log(event);
		console.log(model);
		if (model != modelName) continue;
		const jsonData = JSON.parse(data) as { [key: string]: any };
		if (event == "download_progress") {
			for (const [k, v] of Object.entries(jsonData)) {
				yield {
					progress: v.done,
					total: v.total,
					modelName,
					status: "downloading",
					file: k,
				};
			}
		}
		if (event == "model_status") {
			if (["download_finished", "download_failed"].includes(jsonData.status))
				break;
		}
	}

	eventSource.close();
}
