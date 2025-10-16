import { describe, expect, jest, test } from "bun:test";
import buildProgram from "../buildProgram";
import getClient from "../getClient";
import { $ } from "bun";
import path from "node:path";

jest.setTimeout(-1);

describe.if(process.env.SHABTI_SECURITY_ENABLED == "False")(
	"Security disabled Shabti instance",
	() => {
		const lookup: { [key: string]: any } = {};
		const collectionName = "test_collection";
		test("create collection", async () => {
			const program = await buildProgram();
			await program.parseAsync(["collection", "create", collectionName], {
				from: "user",
			});
			const client = getClient();
			const collections = await client.getCollections();
			const matchingCollection = collections.find(
				(collection) => collection.collectionName == collectionName,
			);
			expect(matchingCollection).toBeTruthy();
			lookup[collectionName] = matchingCollection?.collectionId;
		});
		test("list collections", async () => {
			// TODO: can we call the CLI app programatically instead of running the shell like this?
			const output = await $`bun run index.ts collection list`
				.cwd(path.resolve(path.join(import.meta.dir, "..")))
				.env({ ...process.env })
				.text();
			expect(output).toInclude(collectionName);
		});
		test("delete collection", async () => {
			const program = await buildProgram();
			await program.parseAsync(
				["collection", "delete", lookup[collectionName]],
				{ from: "user" },
			);
			const client = getClient();
			const collections = await client.getCollections();
			const matchingCollection = collections.find(
				(collection) => collection.collectionName == collectionName,
			);
			expect(matchingCollection).toBeFalsy();
		});
	},
);
describe.if(process.env.SHABTI_SECURITY_ENABLED == "True")(
	"Security enabled Shabti instance",
	() => {},
);
