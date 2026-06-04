import { HTTPException } from "hono/http-exception";
import shabtiModels from "../shabti_models.toml";
import { sleep } from "bun";

export default async function* (modelName: string) {
	const modelData = [...shabtiModels.chat, ...shabtiModels.embeddings].find(
		(model) => model.name == modelName,
	);
	if (!modelData) throw new HTTPException(404, { message: "model not found" });
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
		await sleep(1000);
	} while (!["completed", "failed"].includes(status.status));
}
