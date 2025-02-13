import { $ } from "bun"
import { platform } from "node:os"

export default async (command: string) => {
    if (platform() == 'win32') await $`Scripts\\python -m ${{raw: command}}`.cwd("..")
    else await $`./bin/python -m ${{raw: command}}`.cwd("..")
}