import { describe, expect, jest, test } from "bun:test";
import { ShabtiClient } from "../client";
import path = require("node:path");

const test_doc_path = path.join(import.meta.dir, "test_doc.txt");

jest.setTimeout(-1);

describe.if(process.env.SHABTI_SECURITY_ENABLED == "False")(
	"Node Client - Security disabled Shabti instance",
	() => {
		const getClient = () => new ShabtiClient("http://localhost:15131");
		const collectionName = "test_collection_node_client";
		const lookup = {};
		test("create collection", async () => {
			const collectionId = await getClient().createCollection(collectionName);
			expect(collectionId).toBeTruthy();
			lookup[collectionName] = collectionId;
		});
		test("list collections", async () => {
			const collectionList = await getClient().getCollections();
			expect(
				collectionList.some(
					(collection) => collection.collectionName == collectionName,
				),
			).toBeTrue();
		});
		let docId: string;
		test("insert document", async () => {
			const client = getClient();
			for await (const item of await client.insertFiles(
				lookup[collectionName],
				[test_doc_path],
			)) {
				docId = item.documentId;
			}
			expect(docId).toBeTruthy();
		});
		test("insert URL", async () => {
			const client = getClient();
			for await (const item of await client.insertUrls(lookup[collectionName], [
				"https://example.com/",
			])) {
				docId = item.documentId;
			}
			expect(docId).toBeTruthy();
		});
		test("list documents", async () => {
			const docs = await getClient().getDocuments(lookup[collectionName]);
			expect(docs.map((doc) => doc.documentId)).toContain(docId);
		});
		// TODO: test the file route?
		// TODO: can/should we test prompting in some way?
		test("delete document", async () => {
			const client = getClient();
			await client.deleteDocument(lookup[collectionName], docId);
			const docs = await getClient().getDocuments(lookup[collectionName]);
			expect(docs.map((doc) => doc.documentId)).not.toContain(docId);
		});
		test("delete collection", async () => {
			const client = getClient();
			await client.deleteCollection(lookup[collectionName]);
			const collectionList = await client.getCollections();
			expect(
				collectionList.some(
					(collection) => collection.collectionName == collectionName,
				),
			).toBeFalse();
		});
		test("get ollama status", async () => {
			const status = await getClient().ollamaStatus();
			expect(status).toBeTrue();
		});
		test("get OpenSearch status", async () => {
			const status = await getClient().opensearchStatus();
			expect(status).toBeTrue();
		});
		test("get API status", async () => {
			const status = await getClient().apiStatus();
			expect(status).toBeTrue();
		});
	},
);
