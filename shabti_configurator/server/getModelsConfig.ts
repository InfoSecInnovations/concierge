import { file } from "bun";
import shabtiModelsFile from "../shabti_models.ini" with { type: "file" };
import * as ini from "@std/ini";

export default async () => {
	const text = await file(shabtiModelsFile).text();
	const parsed = ini.parse(text) as Record<string, any>;
	return Object.entries(parsed).reduce(
		(acc, [k, v]) => {
			acc[k] = {
				...v,
				tags: v.tags.split(",").map((tag: string) => tag.trim()),
			};
			return acc;
		},
		{} as { [key: string]: any },
	);
};
