import { describe, expect, test } from "bun:test";
import { ShabtiClient } from "./client";

describe.if(process.env.SHABTI_SECURITY_ENABLED == "False")(
	"Security disabled Shabti instance",
	() => {
		const client = new ShabtiClient("http://localhost:15131");
		const collectionName = "test_collection";
		const lookup = {};
		test("create collection", async () => {
			const collectionId = await client.createCollection(collectionName);
			expect(collectionId).toBeTruthy();
			lookup[collectionName] = collectionId;
		});
		test("list collections", async () => {
			const collectionList = await client.getCollections();
			expect(
				collectionList.some(
					(collection) => collection.collectionName == collectionName,
				),
			).toBeTrue();
		});
		test("delete collection", async () => {
			await client.deleteCollection(lookup[collectionName]);
			const collectionList = await client.getCollections();
			expect(
				collectionList.some(
					(collection) => collection.collectionName == collectionName,
				),
			).toBeFalse();
		});
	},
);
