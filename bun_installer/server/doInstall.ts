import { $ } from "bun"
import createCertificates from "./createCertificates"
import path from "node:path"
import { keycloakExists } from "./dockerItemsExist"
import crypto from "node:crypto"
import KcAdminClient from '@keycloak/keycloak-admin-client'
import getEnvPath from "./getEnvPath"
import * as envfile from "envfile"
import getVersion from "./getVersion"
import runPython from "./runPython"
import util from "node:util"
import logMessage from "./logMessage"
import configurePreCommit from "./configurePreCommit"
const exec = util.promisify(await import("node:child_process").then(child_process => child_process.exec))

export default async function* (options: FormData) {
    const environment = options.get("dev_mode")?.toString() == "True" ? "development" : "production"
    // we keep track of the environment variables so we can write to the .env file and the process environment as needed
    const envs: {[key: string]: string} = {}
    const updateEnv = () => {
        Object.entries(envs).forEach(([key, value]) => process.env[key] = value)
        return Bun.write(getEnvPath(), envfile.stringify(envs))
    }
    envs.WEB_HOST = options.get("host")?.toString() || "localhost"
    envs.WEB_PORT = options.get("port")?.toString() || "15130"
    const securityLevel = options.get("security_level")?.toString()
    if (securityLevel && securityLevel != "none") {
        yield logMessage("configuring security...")
        envs.CONCIERGE_SECURITY_ENABLED = "True"
        envs.CONCIERGE_SERVICE = "concierge-enable-security"
        const certDir = path.resolve("self_signed_certificates")        
        await createCertificates(certDir)
        envs.ROOT_CA = path.join(certDir, "root-ca.pem")
        envs.OPENSEARCH_CLIENT_CERT = path.join(certDir, "opensearch-admin-client-cert.pem")
        envs.OPENSEARCH_CLIENT_KEY = path.join(certDir, "opensearch-admin-client-key.pem")
        envs.OPENSEARCH_ADMIN_KEY = path.join(certDir, "opensearch-admin-key.pem")
        envs.OPENSEARCH_ADMIN_CERT = path.join(certDir, "opensearch-admin-cert.pem")
        envs.OPENSEARCH_NODE_CERT = path.join(certDir, "opensearch-node1-cert.pem")
        envs.OPENSEARCH_NODE_KEY = path.join(certDir, "opensearch-node1-key.pem")
        envs.KEYCLOAK_CERT = path.join(certDir, "keycloak-cert.pem")
        envs.KEYCLOAK_CERT_KEY = path.join(certDir, "keycloak-key.pem")
        envs.WEB_CERT = path.join(certDir, "concierge-cert.pem")
        envs.WEB_KEY = path.join(certDir, "concierge-key.pem")
        yield logMessage("configured TLS certificates.")
        if (!await keycloakExists()) {
            const keycloakPassword = options.get("keycloak_password")?.toString()
            // TODO: create error type for this
            if (!keycloakPassword) throw new Error("Keycloak admin password is invalid!")
            // TODO: validate password strength
            // in case we have old postgres data we should remove it to avoid mismatches
            await $`docker volume rm --force concierge_postgres_data`.quiet()
            envs.KEYCLOAK_INITIAL_ADMIN_PASSWORD = keycloakPassword
            const postgresPassword = crypto.randomBytes(25).toString("hex")
            // TODO: validate password strength
            envs.POSTGRES_DB_PASSWORD = postgresPassword
            updateEnv()
            yield logMessage("getting OpenID credentials from Keycloak service. This can take a few minutes!")
            const keycloakComposeFile = path.join("docker_compose", "docker-compose-launch-keycloak.yml")
            // update the keycloak image otherwise it can get overwritten when we launch everything below
            await $`docker compose -f ${keycloakComposeFile} pull`
            await $`docker compose -f ${keycloakComposeFile} up -d`
            // TODO: we need to use the root CA certs rather than disabling verification!
            process.env.NODE_TLS_REJECT_UNAUTHORIZED='0'
            // keep trying this until keycloak is up
            while(true) {
                try {
                    const kcClient = new KcAdminClient({
                        baseUrl: 'https://localhost:8443'
                    })
                    await kcClient.auth({
                        username: 'admin',
                        password: keycloakPassword,
                        grantType: 'password',
                        clientId: 'admin-cli',
                      });
                    const secret = await kcClient.clients.getClientSecret({id: '7a3ec428-36f2-49c4-91b1-8288dc44acb0', realm: 'concierge'})
                    envs.KEYCLOAK_CLIENT_ID = "concierge-auth"
                    envs.KEYCLOAK_CLIENT_SECRET = secret.value!
                    break
                }  
                catch (error) {
                    continue
                }
            }
            yield logMessage("got Keycloak credentials.")
        }
        envs.OPENSEARCH_SERVICE = "opensearch-node-enable-security"
        envs.KEYCLOAK_SERVICE_FILE = "docker-compose-keycloak.yml"
    }
    else {
        envs.CONCIERGE_SERVICE = "concierge"
        envs.CONCIERGE_SECURITY_ENABLED = "False"
        envs.OPENSEARCH_SERVICE = "opensearch-node-disable-security"
        envs.KEYCLOAK_SERVICE_FILE = "docker-compose-blank.yml"
    }
    envs.ENVIRONMENT = environment
    envs.CONCIERGE_VERSION = getVersion()
    envs.OLLAMA_SERVICE = options.has("use_gpu") ? "ollama-gpu" : "ollama"
    await updateEnv()
    yield logMessage("launching Docker containers. This can take quite a long time if this is your first launch or updates have been released to the Docker images...")
    if (environment == "development") {
        await $`docker compose -f ./docker_compose/docker-compose-dev.yml pull`
        await $`docker compose -f ./docker_compose/docker-compose-dev.yml up -d`
        yield logMessage("configuring Python environment...")
        await exec("python3 -m venv ..")
        await runPython("pip install -r dev_requirements.txt")
        await configurePreCommit()
    } 
    else {
        await $`docker compose -f ./docker_compose/docker-compose.yml pull`
        await $`docker compose -f ./docker_compose/docker-compose.yml up -d`
    } 
    if (securityLevel == "demo") {
        yield logMessage("adding demo users")
        envs.IS_SECURITY_DEMO = "True"
        await updateEnv()
        if (environment == "development") await runPython("concierge_scripts.add_keycloak_demo_users")
        else await $`docker exec -d concierge python -m concierge_scripts.add_keycloak_demo_users`
    }
    yield logMessage("pulling language model. This can take quite a long time if you haven't downloaded the model before.")
    // TODO use options.get("language_model")
    await $`docker exec -it ollama ollama pull mistral`
    console.log("Installation done\n")
}