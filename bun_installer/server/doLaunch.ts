import * as envfile from "envfile"
import getEnvPath from "./getEnvPath"
import { $ } from "bun"

export default async (options: FormData, environment = "production") => {
   const envs = envfile.parse(await Bun.file(getEnvPath()).text()) 
   envs.OLLAMA_SERVICE = options.has("use_gpu") ? "ollama-gpu" : "ollama"
   await Bun.write(getEnvPath(), envfile.stringify(envs))
   await $`docker compose -f ./docker_compose/docker-compose.yml up -d`
}