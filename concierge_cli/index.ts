import * as commander from 'commander';
import getAuthClient from './getAuthClient';
import * as dotenv from 'dotenv';
import path from 'node:path'
import { readdir } from 'node:fs/promises';
import * as cliProgress from 'cli-progress';
import getClient from './getClient';
import type { ConciergeAuthorizationClient } from 'concierge-api-client';
import type { ConciergeClient } from 'concierge-api-client';

// we set this to 'executable' when building the standalone
const environment = process.env.CONCIERGE_ENVIRONMENT_TYPE || 'local';
// the environment file is in a different location when running in the executable as opposed to the local code
const envPath = environment == 'executable' ? ['docker_compose', '.env'] : ['..', 'concierge_configurator', 'docker_compose', '.env'];
dotenv.config({ path: path.resolve(path.join(...envPath)) });

const program = new commander.Command();

const authEnabled = process.env.CONCIERGE_SECURITY_ENABLED == 'True'
const client = authEnabled ? await getAuthClient() : await getClient()

const collection = program.command('collection')
if (authEnabled) {
  collection.command('create <name>')
  .requiredOption('-l, --location <location>', 'shared or private')
  .requiredOption('-o, --owner <owner>', 'username this collection will be owned by')
  .action((name, options) => 
    (client as ConciergeAuthorizationClient).createCollection(name, options.location, options.owner)
    .then(collectionId => console.log(`Created collection ${name} with id ${collectionId}`))
  )
}
else {
  collection.command('create <name>')
  .action((name) => {
    (client as ConciergeClient).createCollection(name)
    .then(collectionId => console.log(`Created collection ${name} with id ${collectionId}`))
  })
}

collection.command('delete <collectionId>')
.action((collectionId) => 
  getAuthClient()
  .then(client => client.deleteCollection(collectionId)
  .then(collectionId => console.log(`Deleted collection with id ${collectionId}`))
))
collection.command('list').action(() => 
  getAuthClient()
  .then(client => client.getCollections()
  .then(collections => {
    collections.forEach(collection => console.log(collection))
  })
))

const ingest = program.command('ingest')
ingest.command('directory <directory>')
.description('ingest all files in a directory to a collection')
.requiredOption('-c, --collection <collection>', 'collection id to ingest into')
.action(async (directory, options) => {
  const files = await readdir(directory, { withFileTypes: true, recursive: true });
  const actualFiles = files.filter(file => file.isFile());
  let bar: cliProgress.SingleBar | undefined = undefined
  let currentLabel
  for await (const item of await client.insertFiles(options.collection, actualFiles.map(file => path.join(file.parentPath, file.name)))) {
    if (currentLabel != item.label) {
      if (bar) bar.stop()
      bar = new cliProgress.SingleBar({format: '{bar} {value}/{total} pages {label}'}, cliProgress.Presets.shades_classic)
      bar.start(item.total, 0, {label: item.label});
      currentLabel = item.label
    }
    if (bar) bar.update(item.progress + 1); // progress is 0 indexed but the bar is 1 indexed  
  }
  if (bar) bar.stop();
})
ingest.command('urls <urls...>')
.description('ingest a list of URLs to a collection')
.requiredOption('-c, --collection <collection>', 'collection id to ingest into')
.action(async (urls, options) => {
  let bar: cliProgress.SingleBar | undefined = undefined
  let currentLabel
  for await (const item of await client.insertUrls(options.collection, urls)) {
    if (currentLabel != item.label) {
      if (bar) bar.stop()
      bar = new cliProgress.SingleBar({format: '{bar} {value}/{total} pages {label}'}, cliProgress.Presets.shades_classic)
      bar.start(item.total, 0, {label: item.label});
      currentLabel = item.label
    }
    if (bar) bar.update(item.progress + 1); // progress is 0 indexed but the bar is 1 indexed   
  }
  if (bar) bar.stop();
})

program.command('prompt <userInput>')
.requiredOption('-c, --collection <collection>', 'collection id to source the response from')
.requiredOption('-t, --task <task>', 'task to use for the prompt')
.option('-p, persona <persona>', 'persona to use for the prompt')
.option('-e, --enhancers <enhancers...>', 'enhancers to use for the prompt')
.option('-f, --file <file>', 'file to add information to the prompt context')
.action(async (userInput, options) => {
  let sourceFound = false
  for await (const item of await client.prompt(options.collection, userInput, options.task, options.persona, options.enhancers, options.file)) {
    if (item.source) {
      if (!sourceFound) {
        console.log('Answering using the following sources:')
        sourceFound = true
      }
      console.log(item.source.page_metadata.source)
    } 
    if (item.response) {
      process.stdout.write(item.response)
    }
  }
})

program.parse(Bun.argv)