import path = require("node:path")
import { CollectionInfo } from "./dataTypes"
import { BaseConciergeClient } from "./baseClient"

export class ConciergeClient extends BaseConciergeClient {
  serverUrl: string
  constructor(serverUrl: string) {
    super(serverUrl)
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
}