import { $ } from "bun"
import { platform } from "node:os"

export default (command: string) => {
    if (platform() == 'win32') return $`Scripts\\python -m ${{raw: command}}`.cwd("..")
    return $`./bin/python -m ${{raw: command}}`.cwd("..")
}