import { describe, expect, jest, test } from "bun:test";
import buildProgram from "../buildProgram";
import { $ } from "bun";
import path from "node:path";
import getAuthClient from "../getAuthClient";

jest.setTimeout(-1);

describe.if(process.env.SHABTI_SECURITY_ENABLED == "True")(
	"CLI - Security enabled Shabti instance",
	() => {
		const lookup: { [key: string]: any } = {};
		const documentIds: string[] = [];
		const collectionName = "test_collection_cli";
		test("create collection", async () => {
			const program = await buildProgram();
			await program.parseAsync(
				[
					"collection",
					"create",
					collectionName,
					"--location",
					"shared",
					"--owner",
					"testadmin",
				],
				{
					from: "user",
				},
			);
			const client = await getAuthClient();
			const collections = await client.getCollections();
			const matchingCollection = collections.find(
				(collection) => collection.collectionName == collectionName,
			);
			expect(matchingCollection).toBeTruthy();
			lookup[collectionName] = matchingCollection?.collectionId;
		});
		test("list collections", async () => {
			// TODO: can we call the CLI app programatically instead of running the shell like this?
			const output = await $`bun run index.ts collection list`
				.cwd(path.resolve(path.join(import.meta.dir, "..")))
				.env({ ...process.env })
				.text();
			expect(output).toInclude(collectionName);
		});
		test("ingest file", async () => {
			const filename = "test_doc.txt";
			const filePath = path.join(import.meta.dir, filename);
			const program = await buildProgram();
			await program.parseAsync(
				["ingest", "file", filePath, "--collection", lookup[collectionName]],
				{ from: "user" },
			);
			const client = await getAuthClient();
			const documents = await client.getDocuments(lookup[collectionName]);
			const matchingDocument = documents.find(
				(document) => document.filename == filename,
			);
			expect(matchingDocument).toBeTruthy();
			if (matchingDocument) documentIds.push(matchingDocument.documentId);
		});
		test("ingest urls", async () => {
			const urls = ["https://www.example.com", "https://example.org"];
			const program = await buildProgram();
			await program.parseAsync(
				["ingest", "urls", ...urls, "--collection", lookup[collectionName]],
				{ from: "user" },
			);
			const client = await getAuthClient();
			const documents = await client.getDocuments(lookup[collectionName]);
			const matchingDocuments = documents.filter((document) =>
				urls.includes(document.source),
			);
			expect(matchingDocuments.length == urls.length).toBeTrue();
			documentIds.push(
				...matchingDocuments.map((document) => document.documentId),
			);
		});
		test("ingest directory", async () => {
			const directoryName = "test_dir";
			const directoryFiles = ["test_doc2.txt", "test_doc3.txt"];
			const directoryPath = path.join(import.meta.dir, directoryName);
			const program = await buildProgram();
			await program.parseAsync(
				[
					"ingest",
					"directory",
					directoryPath,
					"--collection",
					lookup[collectionName],
				],
				{ from: "user" },
			);
			const client = await getAuthClient();
			const documents = await client.getDocuments(lookup[collectionName]);
			expect(documents.map((document) => document.filename)).toContainValues(
				directoryFiles,
			);
		});
		test("list documents", async () => {
			const output =
				await $`bun run index.ts document list "${lookup[collectionName]}"`
					.cwd(path.resolve(path.join(import.meta.dir, "..")))
					.env({ ...process.env })
					.text();
			for (const documentId of documentIds) {
				expect(output).toInclude(documentId);
			}
		});
		test("delete documents", async () => {
			const program = await buildProgram();
			await program.parseAsync(
				[
					"document",
					"delete",
					...documentIds,
					"--collection",
					lookup[collectionName],
				],
				{ from: "user" },
			);
			const client = await getAuthClient();
			const documents = await client.getDocuments(lookup[collectionName]);
			expect(
				documents.map((document) => document.documentId),
			).not.toContainAnyValues(documentIds);
		});
		test("delete collection", async () => {
			const program = await buildProgram();
			await program.parseAsync(
				["collection", "delete", lookup[collectionName]],
				{ from: "user" },
			);
			const client = await getAuthClient();
			const collections = await client.getCollections();
			const matchingCollection = collections.find(
				(collection) => collection.collectionName == collectionName,
			);
			expect(matchingCollection).toBeFalsy();
		});
	},
);
