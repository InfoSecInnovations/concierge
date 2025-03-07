import path from "node:path"
import getEnvPath from "./getEnvPath"
import * as envfile from "envfile"

export default async () => {
    const envFile = Bun.file(getEnvPath())
    if (await Promise.all([
        envFile.exists(),
        Bun.file(path.join("docker_compose", "docker-compose.yml")).exists()
    ]).then(res => res.every(exists => exists))) {
        const envs = envfile.parse(await envFile.text())
        if (envs.CONCIERGE_VERSION) return true
        // this isn't exhaustive but should in most cases be sufficient to confirm that the user has an existing configuration
    }
    return false
}