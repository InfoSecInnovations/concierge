import { describe, expect, jest, test } from "bun:test";
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
			const canIngestDocumentUsers = [
				["testadmin", "testadmin", "shared"],
				["testadmin", "testadmin", "private"],
				["testadmin", "testprivate", "private"],
				["testshared", "testadmin", "shared"],
				["testprivate", "testprivate", "private"],
			];
			describe.each(canIngestDocumentUsers)(
				"users can ingest documents",
				(username, owner, location) => {
					collectionIdFixture(owner, location);
					test(`user ${username} can ingest into ${owner}'s ${location} collection`, async () => {
						const client = await getClientForUser(username);
						let docId: string;
						for await (const item of await client.insertFiles(collectionId, [
							test_doc_path,
						])) {
							docId = item.documentId;
						}
						expect(docId).toBeTruthy();
					});
				},
			);
			const cannotIngestDocumentUsers = [
				["testsharedread", "testadmin", "private"],
				["testsharedread", "testadmin", "shared"],
				["testshared", "testadmin", "private"],
				["testprivate", "testadmin", "private"],
				["testprivate", "testadmin", "shared"],
				["testnothing", "testadmin", "shared"],
				["testnothing", "testadmin", "private"],
			];
			describe.each(cannotIngestDocumentUsers)(
				"users cannot ingest documents",
				(username, owner, location) => {
					collectionIdFixture(owner, location);
					test(`user ${username} cannot ingest into ${owner}'s ${location} collection`, async () => {
						const client = await getClientForUser(username);
						expect(async () => {
							for await (const item of await client.insertFiles(collectionId, [
								test_doc_path,
							])) {
							}
						}).toThrow();
					});
				},
			);
			describe("tests with document ID", () => {
				let documentId: string;
				const documentIdFixture = (owner, location) => {
					collectionIdFixture(owner, location);
					beforeEach(async () => {
						for await (const item of await getAdminClient().then((client) =>
							client.insertFiles(collectionId, [test_doc_path]),
						)) {
							documentId = item.documentId;
						}
					});
				};
				const canDeleteDocumentUsers = [
					["testadmin", "testadmin", "shared"],
					["testadmin", "testadmin", "private"],
					["testadmin", "testprivate", "private"],
					["testshared", "testadmin", "shared"],
					["testprivate", "testprivate", "private"],
				];
				describe.each(canDeleteDocumentUsers)(
					"users can delete documents",
					(username, owner, location) => {
						documentIdFixture(owner, location);
						test(`user ${username} can delete document from ${owner}'s ${location} collection`, async () => {
							const userClient = await getClientForUser(username);
							await userClient.deleteDocument(collectionId, documentId);
							const adminClient = await getAdminClient();
							const documents = await adminClient.getDocuments(collectionId);
							expect(
								documents.map((document) => document.documentId),
							).not.toContain(documentId);
						});
					},
				);
				const cannotDeleteDocumentUsers = [
					["testsharedread", "testadmin", "private"],
					["testsharedread", "testadmin", "shared"],
					["testshared", "testadmin", "private"],
					["testprivate", "testadmin", "private"],
					["testprivate", "testadmin", "shared"],
					["testnothing", "testadmin", "shared"],
					["testnothing", "testadmin", "private"],
				];
				describe.each(cannotDeleteDocumentUsers)(
					"users cannot delete documents",
					(username, owner, location) => {
						documentIdFixture(owner, location);
						test(`user ${username} cannot delete document from ${owner}'s ${location} collection`, async () => {
							const userClient = await getClientForUser(username);
							expect(async () => {
								await userClient.deleteDocument(collectionId, documentId);
							}).toThrow();
							const adminClient = await getAdminClient();
							const documents = await adminClient.getDocuments(collectionId);
							expect(
								documents.map((document) => document.documentId),
							).toContain(documentId);
						});
					},
				);
			});
			const canDeleteCollectionUsers = [
				["testadmin", "testadmin", "shared"],
				["testadmin", "testadmin", "private"],
				["testadmin", "testshared", "shared"],
				["testadmin", "testprivate", "private"],
				["testshared", "testadmin", "shared"],
				["testprivate", "testprivate", "private"],
			];
			describe.each(canDeleteCollectionUsers)(
				"users can delete collections",
				(username, owner, location) => {
					collectionIdFixture(owner, location);
					test(`user ${username} can delete ${owner}'s ${location} collection`, async () => {
						const adminClient = await getAdminClient();
						const userClient = await getClientForUser(username);
						await userClient.deleteCollection(collectionId);
						const collections = await adminClient.getCollections();
						expect(
							collections.map((collection) => collection.collectionId),
						).not.toContain(collectionId);
					});
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
			describe.each(cannotDeleteCollectionUsers)(
				"users cannot delete collections",
				(username, owner, location) => {
					collectionIdFixture(owner, location);
					test(`user ${username} cannot delete ${owner}'s ${location} collection`, async () => {
						const adminClient = await getAdminClient();
						const userClient = await getClientForUser(username);
						expect(async () => {
							await userClient.deleteCollection(collectionId);
						}).toThrow();
						const collections = await adminClient.getCollections();
						expect(
							collections.map((collection) => collection.collectionId),
						).toContain(collectionId);
					});
				},
			);
		});
	},
);
