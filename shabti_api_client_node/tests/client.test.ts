import { afterAll, describe, expect, jest, test } from "bun:test";
import { ShabtiClient } from "../client";
import { ShabtiAuthorizationClient } from "../authClient";
import * as openIdClient from "openid-client";
import path = require("node:path");

const test_doc_path = path.join(import.meta.dir, "test_doc.txt");

jest.setTimeout(-1);

describe.if(process.env.SHABTI_SECURITY_ENABLED == "False")(
	"Security disabled Shabti instance",
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
describe.if(process.env.SHABTI_SECURITY_ENABLED == "True")(
	"Security enabled Shabti instance",
	async () => {
		const lookup: { [key: string]: string } = {};
		const getConfig = () =>
			openIdClient.discovery(
				new URL(
					`https://localhost:8443/realms/shabti/.well-known/openid-configuration`,
				),
				process.env.KEYCLOAK_CLIENT_ID!,
				process.env.KEYCLOAK_CLIENT_SECRET!,
			);
		const getClientForUser = async (username: string) => {
			process.env.NODE_TLS_REJECT_UNAUTHORIZED = "0";
			const config = await getConfig();
			const token = await openIdClient.genericGrantRequest(config, "password", {
				username,
				password: "test",
			});
			return new ShabtiAuthorizationClient(
				"https://localhost:15131",
				token,
				config,
			);
		};
		const getAdminClient = async () => {
			process.env.NODE_TLS_REJECT_UNAUTHORIZED = "0";
			const config = await getConfig();
			const token = await openIdClient.clientCredentialsGrant(config);
			return new ShabtiAuthorizationClient(
				"https://localhost:15131",
				token,
				config,
			);
		};
		const canCreateCollectionUsers = [
			["testadmin", "private"],
			["testadmin", "shared"],
			["testshared", "shared"],
			["testprivate", "private"],
		];
		test.each(canCreateCollectionUsers)(
			"user %p can create %p collection",
			async (username, location) => {
				const client = await getClientForUser(username);
				const collectionName = `${username}'s ${location} collection`;
				const collectionId = await client.createCollection(
					collectionName,
					location,
				);
				lookup[collectionName] = collectionId;
				expect(collectionId).toBeTruthy();
			},
		);
		const cannotCreateCollectionUsers = [
			["testshared", "private"],
			["testprivate", "shared"],
			["testsharedread", "private"],
			["testsharedread", "shared"],
			["testnothing", "private"],
			["testnothing", "shared"],
		];
		test.each(cannotCreateCollectionUsers)(
			"user %p can create %p collection",
			async (username, location) => {
				const client = await getClientForUser(username);
				const collectionName = `${username}'s ${location} collection`;
				expect(async () => {
					await client.createCollection(collectionName, location);
				}).toThrow();
			},
		);
		const canReadCollectionUsers = [
			["testadmin", "testadmin's shared collection"],
			["testadmin", "testadmin's private collection"],
			["testadmin", "testprivate's private collection"],
			["testsharedread", "testadmin's shared collection"],
			["testshared", "testadmin's shared collection"],
			["testprivate", "testprivate's private collection"],
		];
		test.each(canReadCollectionUsers)(
			"user %p can read %p",
			async (username, collectionName) => {
				const client = await getClientForUser(username);
				const docs = await client.getDocuments(lookup[collectionName]);
				expect(docs).toBeArray();
			},
		);
		const cannotReadCollectionUsers = [
			["testsharedread", "testadmin's private collection"],
			["testshared", "testadmin's private collection"],
			["testprivate", "testadmin's private collection"],
			["testprivate", "testadmin's shared collection"],
			["testnothing", "testadmin's shared collection"],
			["testnothing", "testadmin's private collection"],
		];
		test.each(cannotReadCollectionUsers)(
			"user %p cannot read %p",
			async (username, collectionName) => {
				const client = await getClientForUser(username);
				expect(async () => {
					await client.getDocuments(lookup[collectionName]);
				}).toThrow();
			},
		);
		const canIngestDocumentUsers = [
			["testadmin", "testadmin's shared collection"],
			["testadmin", "testadmin's private collection"],
			["testadmin", "testprivate's private collection"],
			["testshared", "testadmin's shared collection"],
			["testprivate", "testprivate's private collection"],
		];
		test.each(canIngestDocumentUsers)(
			"user %p can ingest into %p",
			async (username, collectionName) => {
				const client = await getClientForUser(username);
				let docId: string;
				for await (const item of await client.insertFiles(
					lookup[collectionName],
					[test_doc_path],
				)) {
					docId = item.documentId;
				}
				expect(docId).toBeTruthy();
			},
		);
		const cannotIngestDocumentUsers = [
			["testsharedread", "testadmin's private collection"],
			["testsharedread", "testadmin's shared collection"],
			["testshared", "testadmin's private collection"],
			["testprivate", "testadmin's private collection"],
			["testprivate", "testadmin's shared collection"],
			["testnothing", "testadmin's shared collection"],
			["testnothing", "testadmin's private collection"],
		];
		test.each(cannotIngestDocumentUsers)(
			"user %p cannot ingest into %p",
			async (username, collectionName) => {
				const client = await getClientForUser(username);
				expect(async () => {
					for await (const _ of await client.insertFiles(
						lookup[collectionName],
						[test_doc_path],
					)) {
					}
				}).toThrow();
			},
		);
		afterAll(async () => {
			const adminClient = await getAdminClient();
			for (const collectionId of Object.values(lookup)) {
				await adminClient.deleteCollection(collectionId);
			}
		});
	},
);
