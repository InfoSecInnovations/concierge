import { $ } from "bun"
import { platform } from "node:os"

export default () => {
    if (platform() == 'win32') return $`Scripts\\playwright install`.cwd("..")
    return $`./bin/playwright install`.cwd("..")
}