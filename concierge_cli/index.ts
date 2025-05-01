import * as commander from 'commander';
import getAuthClient from './getAuthClient';
import * as dotenv from 'dotenv';
import path from 'node:path'

// we set this to 'executable' when building the standalone
const environment = process.env.CONCIERGE_ENVIRONMENT_TYPE || 'local';
const envPath = environment == 'executable' ? ['docker_compose', '.env'] : ['..', 'concierge_configurator', 'docker_compose', '.env'];
dotenv.config({ path: path.resolve(path.join(...envPath)) });

// TODO: we need a way to point it at the API if you're running it from the command line instead of at the default location

const program = new commander.Command();

const authEnabled = process.env.CONCIERGE_SECURITY_ENABLED == 'True'

const collection = program.command('collection')
if (authEnabled) {
  collection.command('create <name>')
  .option('-l, --location <location>', 'shared or private')
  .option('-o, --owner <owner>', 'username this collection will be owned by')
  .action((name, options) => 
    getAuthClient()
    .then(client => client.createCollection(name, options.location, options.owner)
    .then(collectionId => console.log(`Created collection ${name} with id ${collectionId}`))
  ))
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
}

program.parse(Bun.argv)