import { $ } from "bun"
import { platform } from "node:os"
import path from "node:path"

export default (command: string) => {
    if (platform() == 'win32') return $`Scripts\\python -m ${{raw: command}}`.cwd(path.resolve(path.join("..", "docker_containers", "concierge_api")))
    return $`./bin/python -m ${{raw: command}}`.cwd(path.resolve(path.join("..", "docker_containers", "concierge_api")))
}