import { BaseShabtiClient } from "./baseClient";
import { CollectionInfo } from "./dataTypes";

export class ShabtiClient extends BaseShabtiClient {
	constructor(serverUrl: string) {
		super(serverUrl);
	}

	async createCollection(collectionName: string): Promise<string> {
		const res = await this.makeRequest("POST", "collections", {
			collection_name: collectionName,
		});
		const json = (await res.json()) as any;
		return json.collection_id;
	}

	async getCollections(): Promise<CollectionInfo[]> {
		const res = await this.makeRequest("GET", "collections");
		const json = (await res.json()) as any;
		return json.map(
			(item: any) =>
				new CollectionInfo(item.collection_name, item.collection_id),
		);
	}
}
