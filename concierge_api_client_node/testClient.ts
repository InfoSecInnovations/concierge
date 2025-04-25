import { ConciergeClient } from "./client";

const client = new ConciergeClient("http://localhost:8000")


const run = async () => {
  const collectionId = await client.createCollection("testing").then(collectionId => {
    console.log(collectionId)
    return collectionId
  })
  await client.getCollections().then(collections => collections.forEach(collectionInfo => console.log(collectionInfo)))
  for await (const item of await client.insertFiles(collectionId, ["./test.txt"])) {
    console.log(item)
  }
  await client.deleteCollection(collectionId).then(collectionId => console.log(collectionId))
}

run()