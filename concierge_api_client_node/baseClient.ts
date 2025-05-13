import {openAsBlob} from "node:fs"
import path = require("node:path")
import { CollectionInfo, DocumentInfo, DocumentIngestInfo, ModelLoadInfo, PromptConfigInfo, TaskInfo, WebFile } from "./dataTypes"
import { EXPECTED_CODES } from "./codes"

export class BaseConciergeClient {
  serverUrl: string
  constructor(serverUrl: string) {
    this.serverUrl = serverUrl
  }

  protected async createFormData(name: string, filePaths: string[]) {
    const fd = new FormData()
    for (const filePath of filePaths) {
      const file = await openAsBlob(filePath)
      fd.append(name, file, path.basename(filePath))
    }
    return fd
  }

  protected async makeRequest(method: string, url: string, json?: any, files?: FormData) {
    const body = (() => {
      if (json) return JSON.stringify(json)
      if (files) return files
      return undefined
    })()
    const headers = (() => {
      if (json) return {'Content-Type': 'application/json'}
      return undefined
    })()
    const response = await fetch(new URL(url, this.serverUrl), {
      method,
      body,
      headers
    })
    if (!EXPECTED_CODES.includes(response.status)) {
      const text = await response.text()
      throw new Error(`Request failed with status ${response.status}: ${text}`)
    }
    return response
  }

  protected async streamRequest<T>(method: string, url: string, resultFunction?: { (json: any): T }, json?: any, files?: FormData): Promise<ReadableStream<T>> {
    const res = await this.makeRequest(method, url, json, files);
    const reader = res.body?.getReader();
    if (!reader) {
      throw new Error("Failed to get reader from response body");
    }

    const decoder = new TextDecoder();
    const stream = new ReadableStream<T>({
      async pull(controller) {
        const { done, value } = await reader.read();
        if (done) {
          controller.close();
          return;
        }

        const text = decoder.decode(value, { stream: true });
        const lines = text.split("\n").filter(line => line.trim() !== "");
        for (const line of lines) {
          const json = JSON.parse(line);
          controller.enqueue(resultFunction ? resultFunction(json) : json);
        }
      },
    });

    return stream;
  }

  async deleteCollection(collectionId: string): Promise<string> {
    const res = await this.makeRequest("DELETE", `collections/${collectionId}`)
    const json = await res.json()
    return json.collection_id
  }

  async getDocuments(collectionId: string): Promise<DocumentInfo[]> {
    const res = await this.makeRequest("GET", `collections/${collectionId}/documents`)
    const json = await res.json()
    return json.map(item => new DocumentInfo(item.document_id, item.type, item.source, item.ingest_date, item.page_count, item.vector_count, item.media_type, item.filename))
  }

  async insertFiles(collectionId: string, filePaths: string[]) {
    return this.streamRequest("POST", `collections/${collectionId}/documents/files`, (json) => new DocumentIngestInfo(
      json.progress,
      json.total,
      json.document_id,
      json.document_type,
      json.label
    ), undefined, await this.createFormData("files", filePaths))
  }

  async insertUrls(collectionId: string, urls: string[]) {
    return this.streamRequest("POST", `collections/${collectionId}/documents/urls`, (json) => new DocumentIngestInfo(
      json.progress,
      json.total,
      json.document_id,
      json.document_type,
      json.label
    ), urls )
  }

  async deleteDocument(collectionId: string, documentId: string) {
    const res = await this.makeRequest("DELETE", `collections/${collectionId}/documents/${documentId}`)
    const json = await res.json()
    return json.document_id
  }

  async getTasks(): Promise<{[key: string]: TaskInfo}> {
    const res = await this.makeRequest("GET", "tasks")
    const json = await res.json()
    return Object.entries(json).reduce((acc, [key, value]: any) => {
      return {...acc, [key]: new TaskInfo(value.greeting, value.prompt)}
    }, {})
  }

  async getPersonas(): Promise<{[key: string]: PromptConfigInfo}> {
    const res = await this.makeRequest("GET", "personas")
    const json = await res.json()
    return Object.entries(json).reduce((acc, [key, value]: any) => {
      return {...acc, [key]: new PromptConfigInfo(value.prompt)}
    }, {})
  }

  async getEnhancers(): Promise<{[key: string]: PromptConfigInfo}> {
    const res = await this.makeRequest("GET", "enhancers")
    const json = await res.json()
    return Object.entries(json).reduce((acc, [key, value]: any) => {
      return {...acc, [key]: new PromptConfigInfo(value.prompt)}
    }, {})
  }

  async prompt(collectionId: string, prompt: string, task: string, persona?: string, enhancers?: string[], filePath?: string): Promise<ReadableStream<any>> {
    // TODO: upload file if filePath is provided
    return this.streamRequest("POST", "prompt", null, { collection_id: collectionId, user_input: prompt, task, persona, enhancers })
  }

  async ollamaStatus(): Promise<boolean> {
    const res = await this.makeRequest("GET", "status/ollama")
    const json = await res.json()
    return json.running
  }

  async opensearchStatus(): Promise<boolean> {
    const res = await this.makeRequest("GET", "status/opensearch")
    const json = await res.json()
    return json.running
  }

  async loadModel(modelName: string) {
    return this.streamRequest("POST", "models/pull", json => new ModelLoadInfo(json.progress, json.total, json.model_name), {model_name: modelName})
  }

  async getFile(collectionId: string, documentId: string) {
    const res = await this.makeRequest("GET", `files/${collectionId}/${documentId}`)
    const mediaType = res.headers.get("Content-Type")
    return new WebFile(await res.blob(), mediaType)
  }
}