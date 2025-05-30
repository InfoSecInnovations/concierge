import path from "node:path";
import { ConciergeAuthorizationClient } from "shabti-api-client";
import * as dotenv from "dotenv";
import * as openIdClient from "openid-client";
import getOpenIdConfig from "./getOpenIdConfig";

const run = async () => {
	// TODO: we need to use the root CA certs rather than disabling verification!
	process.env.NODE_TLS_REJECT_UNAUTHORIZED = "0";
	dotenv.config({
		path: path.resolve(
			path.join("..", "shabti_configurator", "docker_compose", ".env"),
		),
	});
	const config = await getOpenIdConfig();
	const token = await openIdClient.genericGrantRequest(config, "password", {
		username: "testadmin",
		password: "test",
	});
	const client = new ConciergeAuthorizationClient(
		"http://localhost:8000",
		token,
		config,
	);

	const collectionId = await client
		.createCollection("testing", "private")
		.then((collectionId) => {
			console.log(collectionId);
			return collectionId;
		});
	await client
		.getCollections()
		.then((collections) =>
			collections.forEach((collectionInfo) => console.log(collectionInfo)),
		);
	let documentId = "";
	for await (const item of await client.insertFiles(collectionId, [
		"./test.txt",
	])) {
		console.log(item);
		documentId = item.documentId;
	}
	for await (const item of await client.insertUrls(collectionId, [
		"https://en.wikipedia.org/wiki/Generative_artificial_intelligence",
	])) {
		console.log(item);
	}
	await client
		.getDocuments(collectionId)
		.then((documents) =>
			documents.forEach((documentInfo) => console.log(documentInfo)),
		);
	for await (const item of await client.prompt(
		collectionId,
		"Where does Generative AI get its data from?",
		"question",
	)) {
		if (item.response) console.log(item.response);
		else console.log(item);
	}
	await client
		.deleteDocument(collectionId, "plaintext", documentId)
		.then((documentId) => console.log(documentId));
	await client
		.deleteCollection(collectionId)
		.then((collectionId) => console.log(collectionId));
};

run();
