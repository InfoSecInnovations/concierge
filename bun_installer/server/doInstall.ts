import dockerComposeZip from "../docker_compose.zip" with { type: "file" }
import { file, $ } from "bun"
import AdmZip from "adm-zip"

export default async (options: FormData) => {
    const buf = await file(dockerComposeZip).arrayBuffer()
    const zip = new AdmZip(Buffer.from(buf))
    zip.extractAllTo(".", true)
    console.log("unzipped Docker Compose")
    console.log(options)
    const envs: {[key: string]: string} = {}
    envs.WEB_HOST = options.get("host")?.toString() || "localhost"
    envs.WEB_PORT = options.get("port")?.toString() || "15130"
    const securityLevel = options.get("security_level")?.toString()
    if (securityLevel && securityLevel != "none") {
        // TODO
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
    Object.entries(envs).forEach(([key, value]) => process.env[key] = value)
    await Bun.write(".env", Object.entries(envs).map(([key, value]) => `${key}=${value}`).join("\n"))
    await $`docker compose -f ./docker_compose/docker-compose.yml up -d`
}