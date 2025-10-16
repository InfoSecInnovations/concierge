import { describe, expect, jest, test } from "bun:test";
import buildProgram from "../buildProgram";
import getClient from "../getClient";

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
