import {openAsBlob} from "node:fs"
import path = require("node:path")
import { CollectionInfo, DocumentInfo, DocumentIngestInfo } from "./dataTypes"
import { EXPECTED_CODES } from "./codes"

export class ConciergeClient {
  serverlUrl: string
  constructor(serverUrl: string) {
    this.serverlUrl = serverUrl
  }

  private async createFormData(name: string, filePaths: string[]) {
    const fd = new FormData()
    for (const filePath of filePaths) {
      const file = await openAsBlob(filePath)
      fd.append(name, file, path.basename(filePath))
    }
    return fd
  }

  private async makeRequest(method: string, url: string, json?: any, files?: FormData) {
    const body = (() => {
      if (json) return JSON.stringify(json)
      if (files) return files
      return undefined
    })()
    const headers = (() => {
      if (json) return {'Content-Type': 'application/json'}
      return undefined
    })()
    const response = await fetch(new URL(url, this.serverlUrl), {
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

  private async streamRequest<T>(method: string, url: string, resultFunction: { (json: any): T }, json?: any, files?: FormData): Promise<ReadableStream<T>> {
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
        console.log(text);
        const lines = text.split("\n").filter(line => line.trim() !== "");
        for (const line of lines) {
          const json = JSON.parse(line);
          controller.enqueue(resultFunction(json));
        }
      },
    });

    return stream;
  }

  async createCollection(collectionName: string): Promise<string> {
    const res = await this.makeRequest("POST", "collections", { collection_name: collectionName })
    const json = await res.json()
    return json.collection_id
  }

  async getCollections(): Promise<CollectionInfo[]> {
    const res = await this.makeRequest("GET", "collections")
    const json = await res.json()
    return json.map(item => new CollectionInfo(item.collection_name, item.collection_id))
  }

  async deleteCollection(collectionId: string): Promise<string> {
    const res = await this.makeRequest("DELETE", `collections/${collectionId}`)
    const json = await res.json()
    return json.collection_id
  }

  async getDocuments(collectionId: string) {
    const res = await this.makeRequest("GET", `collections/${collectionId}/documents`)
    const json = await res.json()
    return json.map(item => new DocumentInfo(item.document_id, item.type, item.source, item.ingest_date, item.index, item.page_count, item.vector_count, item.media_type, item.filename))
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
}