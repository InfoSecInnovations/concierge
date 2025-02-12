import { $ } from "bun"
import util from "node:util"
const exec = util.promisify(await import("node:child_process").then(child_process => child_process.exec))

await exec("python3 -m venv ..")
await $`.\\Scripts\\python -m pip install -r dev_requirements.txt`.cwd("..")