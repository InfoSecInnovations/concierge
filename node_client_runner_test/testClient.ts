import { ConciergeClient } from "concierge-api-client";

const client = new ConciergeClient("http://localhost:8000");

const run = async () => {
	const collectionId = await client
		.createCollection("testing")
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
