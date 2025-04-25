import { ConciergeClient } from "./client";

const client = new ConciergeClient("http://localhost:8000")


const run = async () => {
  await client.createCollection("testing").then(collectionId => console.log(collectionId))
  await client.getCollections().then(collections => collections.forEach(collectionInfo => console.log(collectionInfo)))
}

run()