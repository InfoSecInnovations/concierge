import { describe, expect, test } from "bun:test";
import { ShabtiClient } from "./client";
import { ShabtiAuthorizationClient } from "./authClient";
import * as openIdClient from "openid-client";

describe.if(process.env.SHABTI_SECURITY_ENABLED == "False")(
	"Security disabled Shabti instance",
	() => {
		const getClient = () => new ShabtiClient("http://localhost:15131");
		const collectionName = "test_collection";
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
	},
);
describe.if(process.env.SHABTI_SECURITY_ENABLED == "True")(
	"Security enabled Shabti instance",
	async () => {
		const getClientForUser = async (username: string) => {
			process.env.NODE_TLS_REJECT_UNAUTHORIZED = "0";
			const config = await openIdClient.discovery(
				new URL(
					`https://localhost:8443/realms/shabti/.well-known/openid-configuration`,
				),
				process.env.KEYCLOAK_CLIENT_ID!,
				process.env.KEYCLOAK_CLIENT_SECRET!,
			);
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
	},
);
