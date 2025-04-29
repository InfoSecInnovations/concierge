export class CollectionInfo {
  collectionName: string
  collectionId: string

  constructor(collectionName: string, collectionId: string) {
    this.collectionName = collectionName
    this.collectionId = collectionId
  }
}

export class DocumentInfo {
  type: string
  source: string
  ingestDate: number
  filename?: string
  mediaType?: string
  documentId: string
  index: string
  pageCount: number
  vectorCount: number
  constructor(documentId: string, type: string, source: string, ingestDate: number, index: string, pageCount: number, vectorCount: number, mediaType?: string, filename?: string) {
    this.documentId = documentId
    this.type = type
    this.source = source
    this.ingestDate = ingestDate
    this.index = index
    this.pageCount = pageCount
    this.vectorCount = vectorCount
    this.mediaType = mediaType
    this.filename = filename
  }
}

export class DocumentIngestInfo {
  progress: number
  total: number
  documentId: string
  documentType: string
  label: string

  constructor(progress: number, total: number, documentId: string, documentType: string, label: string) {
    this.progress = progress;
    this.total = total;
    this.documentId = documentId;
    this.documentType = documentType;
    this.label = label;
  }
}

export class PromptConfigInfo {
  prompt?: string
  constructor(prompt?: string) {
    this.prompt = prompt
  }
}

export class TaskInfo extends PromptConfigInfo {
  greeting: string
  constructor(greeting: string, prompt?: string) {
    super(prompt)
    this.greeting = greeting
  }
}

export class ModelLoadInfo {
  progress: number
  total: number
  modelName: string
  constructor(progress: number, total: number, modelName: string) {
    this.progress = progress
    this.total = total
    this.modelName = modelName
  }
}

export class WebFile {
  bytes: Blob
  mediaType: string
  constructor(bytes: Blob, mediaType: string) {
    this.bytes = bytes
    this.mediaType = mediaType
  }
}

