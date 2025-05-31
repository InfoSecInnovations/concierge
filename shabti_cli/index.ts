import { readdir } from "node:fs/promises";
import path from "node:path";
import * as cliProgress from "cli-progress";
import * as commander from "commander";
import type { ShabtiAuthorizationClient } from "shabti-api-client";
import type { ShabtiClient } from "shabti-api-client";
import type {
	DocumentIngestInfo,
	PromptConfigInfo,
} from "shabti-api-client/dist/dataTypes";
import * as dotenv from "dotenv";
import getAuthClient from "./getAuthClient";
import getClient from "./getClient";

// we set this to 'executable' when building the standalone
const environment = process.env.SHABTI_ENVIRONMENT_TYPE || "local";
// the environment file is in a different location when running in the executable as opposed to the local code
const envPath =
	environment == "executable"
		? ["docker_compose", ".env"]
		: ["..", "shabti_configurator", "docker_compose", ".env"];
dotenv.config({ path: path.resolve(path.join(...envPath)) });

const program = new commander.Command();

const authEnabled = process.env.SHABTI_SECURITY_ENABLED == "True";
const client = authEnabled ? await getAuthClient() : getClient();

const collection = program.command("collection");
if (authEnabled) {
	collection
		.command("create <name>")
		.requiredOption("-l, --location <location>", "shared or private")
		.requiredOption(
			"-o, --owner <owner>",
			"username this collection will be owned by",
		)
		.action((name, options) =>
			(client as ShabtiAuthorizationClient)
				.createCollection(name, options.location, options.owner)
				.then((collectionId) =>
					console.log(`Created collection ${name} with id ${collectionId}`),
				),
		);
} else {
	collection.command("create <name>").action((name) => {
		(client as ShabtiClient)
			.createCollection(name)
			.then((collectionId) =>
				console.log(`Created collection ${name} with id ${collectionId}`),
			);
	});
}

collection
	.command("delete <collections...>")
	.description("Delete collections with the specified IDs")
	.action(async (collections) => {
		for (const collectionId of collections) {
			await client
				.deleteCollection(collectionId)
				.then((collectionId) =>
					console.log(`Deleted collection with id ${collectionId}`),
				);
		}
	});
collection
	.command("list")
	.action(() =>
		client
			.getCollections()
			.then((collections) =>
				collections.forEach((collection) => console.log(collection)),
			),
	);

const insert = async (insertStream: ReadableStream<DocumentIngestInfo>) => {
	let bar: cliProgress.SingleBar | undefined = undefined;
	let currentLabel;
	let currentId;
	for await (const item of insertStream) {
		if (currentLabel != item.label) {
			if (bar) {
				bar.stop();
				console.log(`Ingested ${currentLabel} with ID ${currentId}`);
			}
			bar = new cliProgress.SingleBar(
				{ format: "{bar} {value}/{total} pages {label}" },
				cliProgress.Presets.shades_classic,
			);
			bar.start(item.total, 0, { label: item.label });
			currentLabel = item.label;
			currentId = item.documentId;
		}
		if (bar) bar.update(item.progress + 1); // progress is 0 indexed but the bar is 1 indexed
	}
	if (bar) {
		bar.stop();
		console.log(`Ingested ${currentLabel} with ID ${currentId}`);
	}
};

const ingest = program.command("ingest");
ingest
	.command("file <filepath>")
	.description("ingest a file into a collection")
	.requiredOption(
		"-c, --collection <collection>",
		"collection id to ingest into",
	)
	.action(async (filepath, options) =>
		insert(await client.insertFiles(options.collection, [filepath])),
	);
ingest
	.command("directory <directory>")
	.description("ingest all files in a directory to a collection")
	.requiredOption(
		"-c, --collection <collection>",
		"collection id to ingest into",
	)
	.action(async (directory, options) => {
		const files = await readdir(directory, {
			withFileTypes: true,
			recursive: true,
		});
		const actualFiles = files.filter((file) => file.isFile());
		await insert(
			await client.insertFiles(
				options.collection,
				actualFiles.map((file) => path.join(file.parentPath, file.name)),
			),
		);
	});
ingest
	.command("urls <urls...>")
	.description("ingest a list of URLs to a collection")
	.requiredOption(
		"-c, --collection <collection>",
		"collection id to ingest into",
	)
	.action(async (urls, options) =>
		insert(await client.insertUrls(options.collection, urls)),
	);

program
	.command("prompt <userInput>")
	.requiredOption(
		"-c, --collection <collection>",
		"collection id to source the response from",
	)
	.requiredOption("-t, --task <task>", "task to use for the prompt")
	.option("-p, persona <persona>", "persona to use for the prompt")
	.option("-e, --enhancers <enhancers...>", "enhancers to use for the prompt")
	.option("-f, --file <file>", "file to add information to the prompt context")
	.action(async (userInput, options) => {
		let sourceFound = false;
		for await (const item of await client.prompt(
			options.collection,
			userInput,
			options.task,
			options.persona,
			options.enhancers,
			options.file,
		)) {
			if (item.source) {
				if (!sourceFound) {
					console.log("Answering using the following sources:");
					sourceFound = true;
				}
				console.log(item.source.page_metadata.source);
			}
			if (item.response) {
				process.stdout.write(item.response);
			}
		}
	});

const document = program.command("document");
document
	.command("list <collection>")
	.action((collection) =>
		client
			.getDocuments(collection)
			.then((documents) =>
				documents.forEach((document) => console.log(document)),
			),
	);
document
	.command("delete <documents...>")
	.requiredOption(
		"-c, --collection <collection>",
		"collection id containing the documents to be deleted",
	)
	.action(async (documents, options) => {
		for (const documentId of documents) {
			await client
				.deleteDocument(options.collection, documentId)
				.then((documentId) =>
					console.log(`deleted document with id ${documentId}`),
				);
		}
	});

const listPromptConfig = (items: { [key: string]: PromptConfigInfo }) =>
	Object.entries(items).forEach(([key, value]) => {
		console.log(key);
		console.log("");
		if (value.prompt) {
			const splits = value.prompt.split("\n");
			splits.forEach((split) => console.log(split.trim()));
		} else {
			// in reality only the search task should have an empty prompt!
			console.log(
				"this task just searches for matching documents without forming a response",
			);
		}
		console.log("");
	});

program
	.command("task list")
	.action(() => client.getTasks().then((tasks) => listPromptConfig(tasks)));

program
	.command("persona list")
	.action(() =>
		client.getPersonas().then((personas) => listPromptConfig(personas)),
	);

program
	.command("enhancer list")
	.action(() =>
		client.getEnhancers().then((enhancers) => listPromptConfig(enhancers)),
	);

program.command("status").action(async () => {
	console.log(
		`Ollama: ${(await client.ollamaStatus()) ? "online" : "offline"}`,
	);
	console.log(
		`OpenSearch: ${(await client.opensearchStatus()) ? "online" : "offline"}`,
	);
});

program.parse(Bun.argv);
