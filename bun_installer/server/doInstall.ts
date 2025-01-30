import dockerComposeZip from "../docker_compose.zip" with { type: "file" }
import { file, $ } from "bun"
import AdmZip from "adm-zip"
import createCertificates from "./createCertificates"
import path from "node:path"
import { keycloakExists } from "./dockerItemsExist"
import crypto from "node:crypto"
import KcAdminClient from '@keycloak/keycloak-admin-client'
import getEnvPath from "./getEnvPath"

export default async (options: FormData, environment = "production") => {
    // we need the compose files to be available outside of the executable bundle so the shell can use them
    const buf = await file(dockerComposeZip).arrayBuffer()
    const zip = new AdmZip(Buffer.from(buf))
    zip.extractAllTo(".", true)
    console.log("unzipped Docker Compose")
    // we keep track of the environment variables so we can write to the .env file and the process environment as needed
    const envs: {[key: string]: string} = {}
    const updateEnv = () => {
        Object.entries(envs).forEach(([key, value]) => process.env[key] = value)
        return Bun.write(getEnvPath(), Object.entries(envs).map(([key, value]) => `${key}='${value}'`).join("\n"))
    }
    envs.WEB_HOST = options.get("host")?.toString() || "localhost"
    envs.WEB_PORT = options.get("port")?.toString() || "15130"
    const securityLevel = options.get("security_level")?.toString()
    if (securityLevel && securityLevel != "none") {
        envs.CONCIERGE_SECURITY_ENABLED = "True"
        envs.CONCIERGE_SERVICE = "concierge-enable-security"
        const certDir = path.join(import.meta.dir, "..", "self_signed_certificates")
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
        if (!keycloakExists() || !process.env.POSTGRES_DB_PASSWORD || !process.env.KEYCLOAK_CLIENT_ID || !process.env.KEYCLOAK_CLIENT_SECRET) {
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
            const keycloakComposeFile = path.join(import.meta.dir, "..", "docker_compose", "docker-compose-launch-keycloak.yml")
            // update the keycloak image otherwise it can get overwritten when we launch everything below
            await $`docker compose -f ${keycloakComposeFile} pull`
            await $`docker compose -f ${keycloakComposeFile} up -d`
            // TODO: we need to stream this information to the web UI?
            console.log("Waiting for Keycloak to start so we can get the OpenID credentials...")
            console.log("This can take a few minutes, please be patient!")
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
                    envs.KEYCLOAK_CLIENT_SECRET = secret.secretData!
                    break
                }  
                catch (error) {
                    continue
                }
            }
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
    envs.CONCIERGE_VERSION = process.env.npm_package_version!
    envs.OLLAMA_SERVICE = options.has("use_gpu") ? "ollama-gpu" : "ollama"
    await updateEnv()
    await $`docker compose -f ./docker_compose/docker-compose.yml up -d`
    if (securityLevel == "demo") {
        console.log("adding demo users")
        await $`docker exec -d concierge python -m concierge_scripts.add_keycloak_demo_users`
    }
}