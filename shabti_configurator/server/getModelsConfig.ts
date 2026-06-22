import { file } from "bun";
import shabtiModelsFile from "../shabti_models.ini" with { type: "file" };
import { parse } from "ini";

export default async () => {
	const text = await file(shabtiModelsFile).text();
	return parse(text);
};
