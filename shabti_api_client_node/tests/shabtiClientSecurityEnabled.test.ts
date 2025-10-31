import { afterAll, describe, expect, jest, test } from "bun:test";
import { ShabtiAuthorizationClient } from "../authClient";
import * as openIdClient from "openid-client";
import path = require("node:path");
import { randomBytes } from "node:crypto";

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
