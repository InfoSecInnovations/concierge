import * as commander from 'commander';
import getAuthClient from './getAuthClient';

// TODO: load env file from correct location depending on standalone or development environment
// for now you need to pass it in with --env-file=path/to/.env
// also we need a way to point it at the API if you're running it from the command line instead of at the default location

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
  collection.command('list').action(() => console.log('list collections'));
}

program.parse(Bun.argv)