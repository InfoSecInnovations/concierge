import { ShabtiAuthorizationClient } from "@infosecinnovations/shabti-api-client";
import * as openIdClient from "openid-client";
import getOpenIdConfig from "./getOpenIdConfig";
import { randomBytes } from "node:crypto";

// TODO: we need to use the root CA certs rather than disabling verification!
process.env.NODE_TLS_REJECT_UNAUTHORIZED = "0";
const config = await getOpenIdConfig();
const token = await openIdClient.genericGrantRequest(config, "password", {
	username: "testprivate",
	password: "test",
});
const url =
	process.env.API_URL ||
	`https://${process.env.API_HOST || "localhost"}:${process.env.API_PORT || "8000"}`;
const client = new ShabtiAuthorizationClient(url, token, config);
console.log(await client.getUserInfo());
console.log(await client.getPermissions());
const collectionId = await client.createCollection(
	randomBytes(8).toString("hex"),
	"private",
);
console.log(await client.getCollectionScopes(collectionId));
