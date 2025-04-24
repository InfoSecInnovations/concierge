import { $ } from "bun"
import packageJson from "./package.json"
import conciergeUtilPyProject from "../python_packages/concierge_util/pyproject.toml"
import isiUtilPyProject from "../python_packages/isi_util/pyproject.toml"
import conciergeApiPyProject from "../python_packages/concierge_api_client/pyproject.toml"
import conciergeKeycloakPyProject from "../python_packages/concierge_keycloak/pyproject.toml"
import conciergeTypesPyProject from "../python_packages/concierge_types/pyproject.toml"
import path from "node:path"
import util from "node:util"
import runPython from "./server/runPython"
const exec = util.promisify(await import("node:child_process").then(child_process => child_process.exec))
import * as readline from "readline-sync"
import getVersion from "./server/getVersion"
import AdmZip from "adm-zip"

console.log("Concierge release publisher\n")
console.log(`Current version: ${getVersion()}`)
let version = null
while (!version) {
    version = prompt("Input new Concierge version:")
}
packageJson.version = version
await Bun.write("./package.json", JSON.stringify(packageJson, undefined, "\t"))
let pyPiKey: string | null = null
const handlePyPi = async (packageUrlName: string, packageName: string, tomlData: any) => {
    try {
        const pyPiJson: any = await fetch(`https://pypi.org/pypi/${packageUrlName}/json`).then(res => res.json())
        if (pyPiJson.releases[tomlData.project.version]) {
            console.log(`Python package ${packageName} already up to date`)
            return
        }
    }
    catch {} // if the above block fails it probably means the package doesn't exist
    while (!pyPiKey) {
        pyPiKey = readline.question("Please provide your PyPI API key: ", {hideEchoBack: true, mask: ''})
    }
    console.log('\n')
    const packageDir = path.resolve(path.join(import.meta.dir, '..', "python_packages", packageName))
    await $`rm -rf ${path.join(packageDir, "dist")}`
    await exec("python3 -m build", {cwd: packageDir})
    // single backslashes get stripped out by the command line so we need to double them
    await runPython(`twine upload ${path.join(packageDir, "dist").replaceAll("\\", "\\\\")}/* -u __token__ -p ${pyPiKey}`)
}
await handlePyPi("concierge-util", "concierge_util", conciergeUtilPyProject)
await handlePyPi("isi-util", "isi_util", isiUtilPyProject)
await handlePyPi("concierge-api-client", "concierge_api_client", conciergeApiPyProject)
await handlePyPi("concierge-keycloak", "concierge_keycloak", conciergeKeycloakPyProject)
await handlePyPi("concierge-types", "concierge_types", conciergeTypesPyProject)
await $`docker build -t infosecinnovations/concierge:${version} ../docker_containers/concierge_api`
await $`docker image push infosecinnovations/concierge:${version}`
await $`docker build -t infosecinnovations/concierge-web:${version} ../docker_containers/concierge_web`
await $`docker image push infosecinnovations/concierge-web:${version}`
await $`git add -A`
await $`git commit -m 'increment version to ${version}'`
await $`git push`
await $`rm -rf ./dist` // clean dist directory in case we've been running stuff from there
await $`bun run build_win`
await $`bun run build_linux`
await $`bun run build_mac`
const winZip = new AdmZip()
winZip.addLocalFile(path.join("dist", "windows", "concierge.exe"))
winZip.writeZip(path.join("dist", "concierge_win.zip"))
const linuxZip = new AdmZip()
linuxZip.addLocalFile(path.join("dist", "linux", "concierge"))
linuxZip.writeZip(path.join("dist", "concierge_linux.zip"))
const macZip = new AdmZip()
macZip.addLocalFile(path.join("dist", "mac", "concierge"))
macZip.writeZip(path.join("dist", "concierge_mac.zip"))
const gitBranch = await $`git branch --show-current`.text().then(branch => branch.trim())
await $`gh release create ${version} ./dist/*.zip --target ${gitBranch}`