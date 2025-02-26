import { $ } from "bun"
import packageJson from "./package.json"
import conciergeUtilPyProject from "../concierge_packages/concierge_util/pyproject.toml"
import isiUtilPyProject from "../concierge_packages/isi_util/pyproject.toml"
import path from "node:path"
import util from "node:util"
import runPython from "./server/runPython"
const exec = util.promisify(await import("node:child_process").then(child_process => child_process.exec))
import * as readline from "readline-sync"

console.log("Concierge release publisher\n")
let version = null
while (!version) {
    version = prompt("Input new Concierge version:")
}
packageJson.version = version
await Bun.write("./package.json", JSON.stringify(packageJson, undefined, "\t"))
let pyPiKey: string | null = null
const handlePyPi = async (packageUrlName: string, packageName: string, tomlData: any) => {
    const pyPiJson: any = await fetch(`https://pypi.org/pypi/${packageUrlName}/json`).then(res => res.json())
    if (pyPiJson.releases[tomlData.project.version]) {
        console.log(`Python package ${packageName} already up to date`)
        return
    }
    while (!pyPiKey) {
        pyPiKey = readline.question("Please provide your PyPI API key: ", {hideEchoBack: true, mask: ''})
    }
    console.log('\n')
    const packageDir = path.resolve(path.join(import.meta.dir, '..', "concierge_packages", packageName))
    await $`rm -rf ${path.join(packageDir, "dist")}`
    await exec("python3 -m build", {cwd: packageDir})
    // single backslashes get stripped out by the command line so we need to double them
    await runPython(`twine upload ${path.join(packageDir, "dist").replaceAll("\\", "\\\\")}/* -u __token__ -p ${pyPiKey}`)
}
await handlePyPi("concierge-util", "concierge_util", conciergeUtilPyProject)
await handlePyPi("isi-util", "isi_util", isiUtilPyProject)
await $`docker build -t infosecinnovations/concierge:${version} ..`
await $`docker image push infosecinnovations/concierge:${version}`
await $`git add -A`
await $`git commit -m 'increment version to ${version}'`
await $`git push`
await $`rm -rf ./dist` // clean dist directory in case we've been running stuff from there
await $`bun run build_win`
await $`bun run build_linux`
await $`bun run build_mac`
await $`gh release create ${version} ./dist`