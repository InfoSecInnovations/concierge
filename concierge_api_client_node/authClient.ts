import * as client from 'openid-client'
import { EXPECTED_CODES } from './codes'
import { BaseConciergeClient } from './baseClient'
import { AuthzCollectionInfo } from './dataTypes'

class ConciergeTokenExpiredError extends Error {
  constructor(...params: any[]) {
    super(...params)
    this.name = 'TokenExpiredError'
  }
}

class ConciergeAuthenticationError extends Error {
  constructor(...params: any[]) {
    super(...params)
    this.name = 'ConciergeAuthenticationError'
  }
}

export class ConciergeAuthorizationClient extends BaseConciergeClient {
  token: client.TokenEndpointResponse
  openIdConfig: client.Configuration
  refreshTask: Promise<client.TokenEndpointResponse> | null = null

  constructor(serverUrl: string, token: client.TokenEndpointResponse, openIdConfig: client.Configuration) {
    super(serverUrl)
    this.token = token
    this.openIdConfig = openIdConfig
  }

  protected override async makeRequest(method: string, url: string, json?: any, files?: FormData) {
    const doRequest = async (token: client.TokenEndpointResponse) => {
      const body = (() => {
        if (json) return JSON.stringify(json)
        if (files) return files
        return undefined
      })()
      const headers = (() => {
        if (json) return {'Content-Type': 'application/json', 'Authorization': `Bearer ${token.access_token}`}
        return {'Authorization': `Bearer ${token.access_token}`}
      })()
      const response = await fetch(new URL(url, this.serverUrl), {
        method,
        body,
        headers
      })
      if (response.status === 401) {
        throw new ConciergeTokenExpiredError('Token expired')
      }
      if (response.status === 403) {
        throw new ConciergeAuthenticationError('Authentication failed')
      }
      if (!EXPECTED_CODES.includes(response.status)) {
        const text = await response.text()
        throw new Error(`Request failed with status ${response.status}: ${text}`)
      }
      return response
    }
    const currentToken = this.token
    try {
      // if we're already refreshing the token, wait for it to finish
      if (this.refreshTask) {
        await this.refreshTask
      }
      return await doRequest(this.token)
    } catch (error) {
      if (error instanceof ConciergeTokenExpiredError) {
        if (currentToken === this.token) { // this means we're probably using an expired token
          if (!this.refreshTask) {
            this.refreshTask = client.refreshTokenGrant(this.openIdConfig, this.token.refresh_token)
          }
          this.token = await this.refreshTask
          this.refreshTask = null
        } // if we're using a different token from the stored one, it's likely we already did a refresh and we can just rerun
        return await this.makeRequest(method, url, json, files)
      } else {
        throw error
      }
    }
  }

  async createCollection(collectionName: string, location: string, ownerUsername?: string): Promise<string> {
    const res = await this.makeRequest("POST", "collections", { collection_name: collectionName, location, owner_username: ownerUsername })
    const json = await res.json()
    return json.collection_id
  }

  async getCollections(): Promise<AuthzCollectionInfo[]> {
    const res = await this.makeRequest("GET", "collections")
    const json = await res.json()
    return json.map(item => new AuthzCollectionInfo(item.collection_name, item.collection_id, item.location))
  }

  async getUserInfo() {
    const res = await this.makeRequest("GET", "user_info")
    const json = await res.json()
    return json
  }

  async getPermissions() {
    const res = await this.makeRequest("GET", "permissions")
    const json = await res.json()
    return new Set(json)
  }
}