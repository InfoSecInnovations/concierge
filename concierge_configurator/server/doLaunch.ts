import * as envfile from "envfile"
import getEnvPath from "./getEnvPath"
import { $, type Subprocess } from "bun"
import logMessage from "./logMessage"
import { platform } from "node:os"
import path from "node:path"

export default async function* (options: FormData, state: {apiWorker?: Subprocess, webWorker?: Subprocess}) {
   const environment = options.get("environment")
   if (environment == "stop_development") {
      yield logMessage("Stopping Python code running process...")
      if (!state.apiWorker) yield logMessage("no worker!")
      state.apiWorker?.kill("SIGINT")
      await state.apiWorker?.exited
      delete state.apiWorker
      return
   }
   if (environment == "stop_web_development") {
      yield logMessage("Stopping Python code running process...")
      if (!state.webWorker) yield logMessage("no worker!")
      state.webWorker?.kill("SIGINT")
      await state.webWorker?.exited
      delete state.webWorker
      return
   }
   const envs = envfile.parse(await Bun.file(getEnvPath()).text()) 
   envs.OLLAMA_SERVICE = options.has("use_gpu") ? "ollama-gpu" : "ollama"
   yield logMessage(`Launching Shabti ${envs.OLLAMA_SERVICE.endsWith("gpu") ? "with" : "without"} GPU acceleration.`)
   await Bun.write(getEnvPath(), envfile.stringify(envs))

   if (environment == "local") {
      yield logMessage("Building local code files to Docker image. This can take a while depending on your internet connection...")
      await $`docker compose -f ./docker_compose/docker-compose-local.yml build`
      yield logMessage("Launching Docker Compose configuration with locally built image...")
      await $`docker compose -f ./docker_compose/docker-compose-local.yml up -d`
   } 
   else if (environment == "development") {
      yield logMessage("Launching Docker Compose configuration to run Shabti API code locally...")
      await $`docker compose -f ./docker_compose/docker-compose-dev.yml up -d`
      yield logMessage("Running Shabti from local codebase...")
      state.apiWorker = Bun.spawn([platform() == "win32" ? ".\\Scripts\\python" : "./bin/python", "-m", "dev_launcher"], {cwd: path.resolve(path.join("..", "docker_containers", "concierge_api"))})
   } 
   else if (environment == "web_local") {
      yield logMessage("Building local code files to Docker image. This can take a while depending on your internet connection...")
      await $`docker compose -f ./docker_compose/docker-compose-web-local.yml build`
      yield logMessage("Launching Docker Compose configuration with locally built image...")
      await $`docker compose -f ./docker_compose/docker-compose-web-local.yml up -d`
   } 
   else if (environment == "web_development") {
      yield logMessage("Launching Docker Compose configuration to run Shabti Web UI code locally...")
      await $`docker compose -f ./docker_compose/docker-compose-dev.yml up -d`
      yield logMessage("Running Shabti from local codebase...")
      state.webWorker = Bun.spawn([platform() == "win32" ? ".\\Scripts\\python" : "./bin/python", "-m", "dev_launcher"], {cwd: path.resolve(path.join("..", "docker_containers", "concierge_web"))})
   } 
   else {
      yield logMessage("Launching Shabti Docker Compose configuration...")
      await $`docker compose -f ./docker_compose/docker-compose.yml up -d`
   } 
}