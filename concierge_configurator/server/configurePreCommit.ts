import { $ } from "bun"
import { platform } from "node:os"

export default () => {
    if (platform() == 'win32') return $`Scripts\\pre-commit install`.cwd("..")
    return $`./bin/pre-commit install`.cwd("..")
}