// This script was implemented to enable automated tests to set up Concierge
// It provides a Concierge install without having to go through the web UI
// Use at your own risk for other purposes!

import doInstall from "./server/doInstall";
import { parseArgs } from "node:util"

const { values } = parseArgs({
  args: Bun.argv,
  options: {
    'dev-mode': {
      type: 'boolean',
    },
    'host': {
        type: 'string',
        default: 'localhost'
    },
    'port': {
        type: 'string',
        default: '15130'
    },
    'security-level': {
        type: 'string',
        default: 'none'
    },
    'keycloak-password': {
        type: 'string',
        default: ''
    },
    'use-gpu': {
        type: 'boolean'
    }   
  },
  strict: true,
  allowPositionals: true,
});

const options = new FormData()
if (values['dev-mode']) options.set("dev_mode", "True")
options.set('host', values['host'])
options.set('port', values['port'])
options.set('security_level', values['security-level'])
if (values['keycloak-password']) options.set('keycloak_password', values['keycloak-password'])
if (values['use-gpu']) options.set("use_gpu", 'True')

for await (const _ of doInstall(options, false)) { // we don't configure the venv because we assume it already exists and we don't want to break it

}