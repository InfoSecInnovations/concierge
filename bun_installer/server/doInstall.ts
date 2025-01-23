import dockerComposeZip from "../docker_compose.zip" with { type: "file" }
import { file, $ } from "bun"
import AdmZip from "adm-zip"

export default async (options: FormData) => {
    // we need the compose files to be available outside of the executable bundle so the shell can use them
    const buf = await file(dockerComposeZip).arrayBuffer()
    const zip = new AdmZip(Buffer.from(buf))
    zip.extractAllTo(".", true)
    console.log("unzipped Docker Compose")
    // we keep track of the environment variables so we can write to the .env file and the process environment as needed
    const envs: {[key: string]: string} = {}
    const updateEnv = () => {
        Object.entries(envs).forEach(([key, value]) => process.env[key] = value)
        return Bun.write(".env", Object.entries(envs).map(([key, value]) => `${key}=${value}`).join("\n"))
    }
    envs.WEB_HOST = options.get("host")?.toString() || "localhost"
    envs.WEB_PORT = options.get("port")?.toString() || "15130"
    const securityLevel = options.get("security_level")?.toString()
    if (securityLevel && securityLevel != "none") {
        envs.CONCIERGE_SECURITY_ENABLED = "True"
        envs.CONCIERGE_SERVICE = "concierge-enable-security"
        // TODO: certificate generation
        // TODO: set cert env vars
        // TODO: if keycloak isn't running
            // TODO: configure keycloak and postgres initial passwords
            // TODO: run keycloak compose
            // TODO: get keycloak client secret
        envs.OPENSEARCH_SERVICE = "opensearch-node-enable-security"
        envs.KEYCLOAK_SERVICE_FILE = "docker-compose-keycloak.yml"
    }
    else {
        envs.CONCIERGE_SERVICE = "concierge"
        envs.CONCIERGE_SECURITY_ENABLED = "False"
        envs.OPENSEARCH_SERVICE = "opensearch-node-disable-security"
        envs.KEYCLOAK_SERVICE_FILE = "docker-compose-blank.yml"
    }
    envs.ENVIRONMENT = "production"
    envs.CONCIERGE_VERSION = "0.5a13"
    envs.OLLAMA_SERVICE = options.has("use_gpu") ? "ollama-gpu" : "ollama"
    await updateEnv()
    await $`docker compose -f ./docker_compose/docker-compose.yml up -d`
}