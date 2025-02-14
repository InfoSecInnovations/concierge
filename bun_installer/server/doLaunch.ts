import * as envfile from "envfile"
import getEnvPath from "./getEnvPath"
import { $, type Subprocess } from "bun"
import logMessage from "./logMessage"
import { platform } from "node:os"
import path from "node:path"

export default async function* (options: FormData, state: {worker?: Subprocess}) {
   const environment = options.get("environment")
   if (environment == "stop_development") {
      yield logMessage("Stopping Python code running process...")
      if (!state.worker) yield logMessage("no worker!")
      state.worker?.kill("SIGINT")
      await state.worker?.exited
      delete state.worker
      return
   }
   const envs = envfile.parse(await Bun.file(getEnvPath()).text()) 
   envs.OLLAMA_SERVICE = options.has("use_gpu") ? "ollama-gpu" : "ollama"
   yield logMessage(`Launching Concierge ${envs.OLLAMA_SERVICE.endsWith("gpu") ? "with" : "without"} GPU acceleration.`)
   await Bun.write(getEnvPath(), envfile.stringify(envs))

   if (environment == "local") {
      yield logMessage("Building local code files to Docker image. This can take a while depending on your internet connection...")
      await $`docker compose -f ./docker_compose/docker-compose-local.yml build`
      yield logMessage("Launching Docker Compose configuration with locally built image...")
      await $`docker compose -f ./docker_compose/docker-compose-local.yml up -d`
   } 
   else if (environment == "development") {
      yield logMessage("Launching Docker Compose configuration to run Concierge code locally...")
      await $`docker compose -f ./docker_compose/docker-compose-dev.yml up -d`
      yield logMessage("Running Concierge from local codebase...")
      state.worker = Bun.spawn([platform() == "win32" ? ".\\Scripts\\python" : "./bin/python", "-m", "dev_launcher"], {cwd: path.resolve("..")})
   } 
   else {
      yield logMessage("Launching Concierge Docker Compose configuration...")
      await $`docker compose -f ./docker_compose/docker-compose.yml up -d`
   } 
}