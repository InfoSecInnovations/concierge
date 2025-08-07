import { openAsBlob } from "node:fs";
import path = require("node:path");
import { EXPECTED_CODES } from "./codes";
import {
	CollectionInfo,
	DocumentInfo,
	DocumentIngestInfo,
	ModelLoadInfo,
	PromptConfigInfo,
	TaskInfo,
	UnsupportedFileError,
	WebFile,
} from "./dataTypes";

export class BaseShabtiClient {
	serverUrl: string;
	constructor(serverUrl: string) {
		this.serverUrl = serverUrl;
	}

	protected async createFormData(name: string, filePaths: string[]) {
		const fd = new FormData();
		for (const filePath of filePaths) {
			const file = await openAsBlob(filePath);
			fd.append(name, file, path.basename(filePath));
		}
		return fd;
	}

	protected async makeRequest(
		method: string,
		url: string,
		json?: any,
		files?: FormData,
	) {
		const body = (() => {
			if (json) return JSON.stringify(json);
			if (files) return files;
			return undefined;
		})();
		const headers = (() => {
			if (json) return { "Content-Type": "application/json" };
			return undefined;
		})();
		const response = await fetch(new URL(url, this.serverUrl), {
			method,
			body,
			headers,
		});
		if (!EXPECTED_CODES.includes(response.status)) {
			const text = await response.text();
			throw new Error(`Request failed with status ${response.status}: ${text}`);
		}
		return response;
	}

	protected async streamRequest<T>(
		method: string,
		url: string,
		resultFunction?: (json: any) => T,
		json?: any,
		files?: FormData,
	): Promise<ReadableStream<T>> {
		const res = await this.makeRequest(method, url, json, files);
		const reader = res.body.getReader();
		const decoder = new TextDecoder();
		let current = "";
		const stream = new ReadableStream<T>({
			async pull(controller) {
				const { done, value } = await reader.read();
				if (done) {
					controller.close();
					return;
				}
				const text = decoder.decode(value, { stream: true });
				// it's possible we don't receive a full line in one chunk if the lines are long
				const splits = text.split("\n");
				if (splits.length == 1) {
					// this means there was no newline in the whole chunk
					current += splits[0];
				} else if (splits.length) {
					// there was a newline somewhere
					// we add the first split to the currently collected text
					const lines = [current + splits[0], ...splits.slice(1, -1)];
					// the last split is either empty due to the newline being at the end or contains the start of a new chunk
					current = splits[splits.length - 1];
					for (const line of lines.filter((line) => line.trim())) {
						const json = JSON.parse(line);
						controller.enqueue(resultFunction ? resultFunction(json) : json);
					}
				}
			},
		});

		return stream;
	}

	async deleteCollection(collectionId: string): Promise<string> {
		const res = await this.makeRequest("DELETE", `collections/${collectionId}`);
		const json = await res.json();
		return json.collection_id;
	}

	async getDocuments(collectionId: string): Promise<DocumentInfo[]> {
		const res = await this.makeRequest(
			"GET",
			`collections/${collectionId}/documents`,
		);
		const json = await res.json();
		return json.map(
			(item) =>
				new DocumentInfo(
					item.document_id,
					item.type,
					item.source,
					item.ingest_date,
					item.page_count,
					item.vector_count,
					item.media_type,
					item.filename,
				),
		);
	}

	async insertFiles(collectionId: string, filePaths: string[]) {
		return this.streamRequest(
			"POST",
			`collections/${collectionId}/documents/files`,
			(json) => {
				if (json.error) {
					if (json.error == "UnsupportedFileError")
						return new UnsupportedFileError(json.message, json.filename);
					throw new Error(`${json.error}: ${json.message}`);
				}
				return new DocumentIngestInfo(
					json.progress,
					json.total,
					json.document_id,
					json.document_type,
					json.label,
				);
			},
			undefined,
			await this.createFormData("files", filePaths),
		);
	}

	async insertUrls(collectionId: string, urls: string[]) {
		return this.streamRequest(
			"POST",
			`collections/${collectionId}/documents/urls`,
			(json) =>
				new DocumentIngestInfo(
					json.progress,
					json.total,
					json.document_id,
					json.document_type,
					json.label,
				),
			urls,
		);
	}

	async deleteDocument(collectionId: string, documentId: string) {
		const res = await this.makeRequest(
			"DELETE",
			`collections/${collectionId}/documents/${documentId}`,
		);
		const json = await res.json();
		return json.document_id;
	}

	async getTasks(): Promise<{ [key: string]: TaskInfo }> {
		const res = await this.makeRequest("GET", "tasks");
		const json = await res.json();
		return Object.entries(json).reduce((acc, [key, value]: any) => {
			return { ...acc, [key]: new TaskInfo(value.greeting, value.prompt) };
		}, {});
	}

	async getPersonas(): Promise<{ [key: string]: PromptConfigInfo }> {
		const res = await this.makeRequest("GET", "personas");
		const json = await res.json();
		return Object.entries(json).reduce((acc, [key, value]: any) => {
			return { ...acc, [key]: new PromptConfigInfo(value.prompt) };
		}, {});
	}

	async getEnhancers(): Promise<{ [key: string]: PromptConfigInfo }> {
		const res = await this.makeRequest("GET", "enhancers");
		const json = await res.json();
		return Object.entries(json).reduce((acc, [key, value]: any) => {
			return { ...acc, [key]: new PromptConfigInfo(value.prompt) };
		}, {});
	}

	async prompt(
		collectionId: string,
		prompt: string,
		task: string,
		persona?: string,
		enhancers?: string[],
		filePath?: string,
	): Promise<ReadableStream<any>> {
		const fileId = await (async () => {
			if (filePath) {
				const res = await this.makeRequest(
					"POST",
					"/prompt/source_file",
					undefined,
					await this.createFormData("file", [filePath]),
				).then((res) => res.json());
				return res.id;
			}
			return undefined;
		})();

		return this.streamRequest("POST", "prompt", null, {
			collection_id: collectionId,
			user_input: prompt,
			task,
			persona,
			enhancers,
			file_id: fileId,
		});
	}

	async apiStatus(): Promise<boolean> {
		try {
			const res = await this.makeRequest("GET", "/");
			return res.status == 200;
		} catch {
			return false;
		}
	}

	async ollamaStatus(): Promise<boolean> {
		const res = await this.makeRequest("GET", "status/ollama");
		const json = await res.json();
		return json.running;
	}

	async opensearchStatus(): Promise<boolean> {
		const res = await this.makeRequest("GET", "status/opensearch");
		const json = await res.json();
		return json.running;
	}

	async loadModel(modelName: string) {
		return this.streamRequest(
			"POST",
			"models/pull",
			(json) => new ModelLoadInfo(json.progress, json.total, json.model_name),
			{ model_name: modelName },
		);
	}

	async getFile(collectionId: string, documentId: string) {
		const res = await this.makeRequest(
			"GET",
			`files/${collectionId}/${documentId}`,
		);
		const mediaType = res.headers.get("Content-Type");
		return new WebFile(await res.blob(), mediaType);
	}
}
