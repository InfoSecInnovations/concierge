export class CollectionInfo {
	collectionName: string;
	collectionId: string;

	constructor(collectionName: string, collectionId: string) {
		this.collectionName = collectionName;
		this.collectionId = collectionId;
	}
}

export class UserInfo {
	username: string;
	userId: string;

	constructor(username: string, userId: string) {
		this.username = username;
		this.userId = userId;
	}
}

export class AuthzCollectionInfo extends CollectionInfo {
	location: string;
	owner: UserInfo;

	constructor(
		collectionName: string,
		collectionId: string,
		location: string,
		owner: UserInfo,
	) {
		super(collectionName, collectionId);
		this.location = location;
		this.owner = owner;
	}
}

export class DocumentInfo {
	source: string;
	ingestDate: number;
	filename?: string;
	mediaType: string;
	documentId: string;
	pageCount: number;
	vectorCount: number;
	constructor(
		documentId: string,
		source: string,
		ingestDate: number,
		pageCount: number,
		vectorCount: number,
		mediaType: string,
		filename?: string,
	) {
		this.documentId = documentId;
		this.source = source;
		this.ingestDate = ingestDate;
		this.pageCount = pageCount;
		this.vectorCount = vectorCount;
		this.mediaType = mediaType;
		this.filename = filename;
	}
}

export class DocumentList {
	documents: DocumentInfo[];
	totalHits: number;
	totalDocuments: number;
	constructor(
		documents: DocumentInfo[],
		totalHits: number,
		totalDocuments: number,
	) {
		this.documents = documents;
		this.totalHits = totalHits;
		this.totalDocuments = totalDocuments;
	}
}

export class DocumentIngestInfo {
	progress: number;
	total: number;
	documentId: string;
	documentType: string;
	label: string;

	constructor(
		progress: number,
		total: number,
		documentId: string,
		documentType: string,
		label: string,
	) {
		this.progress = progress;
		this.total = total;
		this.documentId = documentId;
		this.documentType = documentType;
		this.label = label;
	}
}

export class UnsupportedFileError {
	message: string;
	filename: string;

	constructor(message: string, filename: string) {
		this.message = message;
		this.filename = filename;
	}
}

export class PromptConfigInfo {
	prompt?: string;
	constructor(prompt?: string) {
		this.prompt = prompt;
	}
}

export class TaskInfo extends PromptConfigInfo {
	greeting: string;
	constructor(greeting: string, prompt?: string) {
		super(prompt);
		this.greeting = greeting;
	}
}

export class ModelLoadInfo {
	progress: number;
	total: number;
	modelName: string;
	constructor(progress: number, total: number, modelName: string) {
		this.progress = progress;
		this.total = total;
		this.modelName = modelName;
	}
}

export class WebFile {
	bytes: Blob;
	mediaType: string;
	constructor(bytes: Blob, mediaType: string) {
		this.bytes = bytes;
		this.mediaType = mediaType;
	}
}
