import { afterAll, describe, expect, jest, test } from "bun:test";
import { ShabtiAuthorizationClient } from "../authClient";
import * as openIdClient from "openid-client";
import path = require("node:path");
import { randomBytes } from "node:crypto";
import { afterEach, beforeEach } from "node:test";

const test_doc_path = path.join(import.meta.dir, "test_doc.txt");

jest.setTimeout(-1);

describe.if(process.env.SHABTI_SECURITY_ENABLED == "True")(
	"Node Client - Security enabled Shabti instance",
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
		const createCollectionForUser = (owner: string, location: string) =>
			getAdminClient().then((client) =>
				client.createCollection(
					randomBytes(8).toString("hex"),
					location,
					owner,
				),
			);
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
				expect(collectionId).toBeTruthy();
				lookup[collectionName] = collectionId;
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
		describe("tests with collection ID", () => {
			let collectionId: string;
			const collectionIdFixture = (owner, location) => {
				beforeEach(async () => {
					collectionId = await createCollectionForUser(owner, location);
				});
				afterEach(async () => {
					try {
						await getAdminClient().then((client) =>
							client.deleteCollection(collectionId),
						);
					} catch {}
				});
			};
			const canReadCollectionUsers = [
				["testadmin", "testadmin", "shared"],
				["testadmin", "testadmin", "private"],
				["testadmin", "testprivate", "private"],
				["testsharedread", "testadmin", "shared"],
				["testshared", "testadmin", "shared"],
				["testprivate", "testprivate", "private"],
			];
			describe.each(canReadCollectionUsers)(
				"users can read collection",
				(username, owner, location) => {
					collectionIdFixture(owner, location);
					test(`user ${username} can read ${owner}'s ${location} collection`, async () => {
						const client = await getClientForUser(username);
						const docs = await client.getDocuments(collectionId);
						expect(docs).toBeArray();
					});
				},
			);
			const cannotReadCollectionUsers = [
				["testsharedread", "testadmin", "private"],
				["testshared", "testadmin", "private"],
				["testprivate", "testadmin", "private"],
				["testprivate", "testadmin", "shared"],
				["testnothing", "testadmin", "shared"],
				["testnothing", "testadmin", "private"],
			];
			describe.each(cannotReadCollectionUsers)(
				"users cannot read collection",
				(username, owner, location) => {
					collectionIdFixture(owner, location);
					test(`user ${username} cannot read ${owner}'s ${location} collection`, async () => {
						const client = await getClientForUser(username);
						expect(async () => {
							await client.getDocuments(collectionId);
						}).toThrow();
					});
				},
			);
		});
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
		const canDeleteDocumentUsers = [
			["testadmin", "testadmin's shared collection"],
			["testadmin", "testadmin's private collection"],
			["testadmin", "testprivate's private collection"],
			["testshared", "testadmin's shared collection"],
			["testprivate", "testprivate's private collection"],
		];
		test.each(canDeleteDocumentUsers)(
			"user %p can delete document from collection %p",
			async (username, collectionName) => {
				const adminClient = await getAdminClient();
				let docId: string;
				for await (const item of await adminClient.insertFiles(
					lookup[collectionName],
					[test_doc_path],
				)) {
					docId = item.documentId;
				}
				const userClient = await getClientForUser(username);
				await userClient.deleteDocument(lookup[collectionName], docId);
				const documents = await adminClient.getDocuments(
					lookup[collectionName],
				);
				expect(documents.map((document) => document.documentId)).not.toContain(
					docId,
				);
			},
		);
		const cannotDeleteDocumentUsers = [
			["testsharedread", "testadmin's private collection"],
			["testsharedread", "testadmin's shared collection"],
			["testshared", "testadmin's private collection"],
			["testprivate", "testadmin's private collection"],
			["testprivate", "testadmin's shared collection"],
			["testnothing", "testadmin's shared collection"],
			["testnothing", "testadmin's private collection"],
		];
		test.each(cannotDeleteDocumentUsers)(
			"user %p cannot delete document from collection %p",
			async (username, collectionName) => {
				const adminClient = await getAdminClient();
				let docId: string;
				for await (const item of await adminClient.insertFiles(
					lookup[collectionName],
					[test_doc_path],
				)) {
					docId = item.documentId;
				}
				const userClient = await getClientForUser(username);
				expect(async () => {
					await userClient.deleteDocument(lookup[collectionName], docId);
				}).toThrow();
				const documents = await adminClient.getDocuments(
					lookup[collectionName],
				);
				expect(documents.map((document) => document.documentId)).toContain(
					docId,
				);
			},
		);
		const canDeleteCollectionUsers = [
			["testadmin", "testadmin", "shared"],
			["testadmin", "testadmin", "private"],
			["testadmin", "testshared", "shared"],
			["testadmin", "testprivate", "private"],
			["testshared", "testadmin", "shared"],
			["testprivate", "testprivate", "private"],
		];
		test.each(canDeleteCollectionUsers)(
			"user %p can delete collection belonging to %p of type %p",
			async (username, owner, location) => {
				const adminClient = await getAdminClient();
				const collectionName = randomBytes(8).toString("hex");
				const collectionId = await adminClient.createCollection(
					collectionName,
					location,
					owner,
				);
				const userClient = await getClientForUser(username);
				await userClient.deleteCollection(collectionId);
				const collections = await adminClient.getCollections();
				expect(
					collections.map((collection) => collection.collectionId),
				).not.toContain(collectionId);
			},
		);
		const cannotDeleteCollectionUsers = [
			["testsharedread", "testadmin", "shared"],
			["testsharedread", "testadmin", "private"],
			["testshared", "testadmin", "private"],
			["testprivate", "testadmin", "private"],
			["testprivate", "testadmin", "shared"],
			["testnothing", "testadmin", "shared"],
			["testnothing", "testadmin", "private"],
		];
		test.each(cannotDeleteCollectionUsers)(
			"user %p cannot delete collection belonging to %p of type %p",
			async (username, owner, location) => {
				const adminClient = await getAdminClient();
				const collectionName = randomBytes(8).toString("hex");
				const collectionId = await adminClient.createCollection(
					collectionName,
					location,
					owner,
				);
				const userClient = await getClientForUser(username);
				expect(async () => {
					await userClient.deleteCollection(collectionId);
				}).toThrow();
				const collections = await adminClient.getCollections();
				expect(
					collections.map((collection) => collection.collectionId),
				).toContain(collectionId);
			},
		);
		afterAll(async () => {
			const adminClient = await getAdminClient();
			for (const collectionId of Object.values(lookup)) {
				// collection may have already been deleted by a test
				try {
					await adminClient.deleteCollection(collectionId);
				} catch {}
			}
		});
	},
);
