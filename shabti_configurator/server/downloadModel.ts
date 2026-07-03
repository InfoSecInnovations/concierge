import { HTTPException } from "hono/http-exception";
import { sleep } from "bun";
import getModelsConfig from "../getModelsConfig";
import { createEventSource } from "eventsource-client";

const TIMEOUT = 10000;
const HEALTH_POLL_INTERVAL = 300;

export default async function* (modelName: string) {
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
	console.log(`loading ${modelData.hf}`);
	// this must be the actual repo instead of modelName
	// unfortunately llama.cpp won't show progress when pulling a model saved in the ini file?
	const res = await fetch("http://localhost:11434/models", {
		body: JSON.stringify({ model: modelData.hf }),
		method: "POST",
	});
	if (res.status != 200) {
		const json = (await res.json()) as any;
		// if the model already exists we don't need to download it again
		if (res.status == 400 && json.error?.message?.includes("already exists"))
			return;
		console.log(json);
		throw new HTTPException(500, { message: json.error.error });
	}
	const eventSource = createEventSource("http://localhost:11434/models/sse");
	for await (const { data } of eventSource) {
		const jsonData = JSON.parse(data) as { [key: string]: any };
		if (jsonData.model != modelData.hf) continue;
		if (jsonData.event == "download_progress") {
			for (const [k, v] of Object.entries(
				jsonData.data.progress as { [key: string]: any },
			)) {
				yield {
					progress: v.done,
					total: v.total,
					modelName,
					status: "downloading",
					file: k,
				};
			}
		}
		if (["download_finished", "download_failed"].includes(jsonData.event))
			// TODO: handle failed state
			break;
	}

	eventSource.close();
}
