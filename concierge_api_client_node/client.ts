import {openAsBlob} from "node:fs"
import path = require("node:path")
import { CollectionInfo } from "./dataTypes"

export class ConciergeClient {
  serverlUrl: string
  constructor(serverUrl: string) {
    this.serverlUrl = serverUrl
  }

  private async createFormData(name: string, filePaths: string[]) {
    const fd = new FormData()
    for (const filePath in filePaths) {
      const file = await openAsBlob(filePath)
      fd.append(name, file, path.basename(filePath))
    }
    return fd
  }
  private makeRequest(method: string, url: string, json?: any, files?: FormData) {
    const body = (() => {
      if (json) return JSON.stringify(json)
      if (files) return files
      return undefined
    })()
    const headers = (() => {
      if (json) return {'Content-Type': 'application/json'}
      if (files) return {'Content-Type': 'application/x-www-form-urlencoded'}
      return undefined
    })()
    return fetch(new URL(url, this.serverlUrl), {
      method,
      body,
      headers
    })
  }

  async createCollection(collectionName: string) {
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