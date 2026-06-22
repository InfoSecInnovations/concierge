import { HTTPException } from "hono/http-exception";
import { sleep } from "bun";
import getModelsConfig from "./getModelsConfig";

const TIMEOUT = 10000;
const HEALTH_POLL_INTERVAL = 300;
const DOWNLOAD_POLL_INTERVAL = 1000;

export default async function* (modelName: string) {
	const shabtiModels = await getModelsConfig();
	const modelData = [...shabtiModels.chat, ...shabtiModels.embeddings].find(
		(model) => model.name == modelName,
	);
	if (!modelData) throw new HTTPException(404, { message: "model not found" });
	const start = performance.now();
	while (performance.now() - start < TIMEOUT) {
		try {
			if (
				await fetch("http://localhost:8090/api/health").then(
					(res) => res.status == 200,
				)
			)
				break;
		} catch {}
		sleep(HEALTH_POLL_INTERVAL);
	}
	const res = (await fetch("http://localhost:8090/api/download", {
		body: JSON.stringify({ repo: modelData.hf }),
		method: "POST",
	}).then((res) => res.json())) as any;
	const jobId =
		res.id ||
		(await fetch("http://localhost:8090/api/jobs")
			.then((res) => res.json)
			.then(
				(res: any) => res.jobs.find((job: any) => job.repo == modelData.hf)?.id,
			));
	if (typeof jobId == "undefined")
		throw new HTTPException(404, { message: "model loading job not found" });
	const getStatus = () =>
		fetch(`http://localhost:8090/api/jobs/${jobId}`).then((res) =>
			res.json(),
		) as any;
	let status;
	do {
		status = await getStatus();
		yield {
			progress: status.progress.downloadedBytes,
			total: status.progress.totalBytes,
			modelName,
			status: status.status,
		};
		await sleep(DOWNLOAD_POLL_INTERVAL);
	} while (!["completed", "failed"].includes(status.status));
}
