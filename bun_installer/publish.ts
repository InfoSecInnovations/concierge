import { $ } from "bun"
import packageJson from "./package.json"
import conciergeUtilPyProject from "../concierge_packages/concierge_util/pyproject.toml"
import isiUtilPyProject from "../concierge_packages/isi_util/pyproject.toml"
import path from "node:path"
import util from "node:util"
import runPython from "./server/runPython"
const exec = util.promisify(await import("node:child_process").then(child_process => child_process.exec))

console.log("Concierge release publisher\n")
let version = null
while (!version) {
    version = prompt("Input new Concierge version:")
}
packageJson.version = version
await Bun.write("./package.json", JSON.stringify(packageJson, undefined, "\t"))
await $`git add -A`
await $`git commit -m 'increment version to ${version}'`
await $`git push`
let pyPiKey: string | null = null
const handlePyPi = async (packageUrlName: string, packageName: string, tomlData: any) => {
    const pyPiJson: any = await fetch(`https://pypi.org/pypi/${packageUrlName}/json`).then(res => res.json())
    if (pyPiJson.releases[tomlData.version]) {
        console.log(`Python package ${packageName} already up to date`)
        return
    }
    while (!pyPiKey) {
        pyPiKey = prompt("Please provide your PyPI API key")
    }
    const packageDir = path.resolve(path.join(import.meta.dir, '..', "concierge_packages", packageName))
    await $`rm -rf ${path.join(packageDir, "dist")}`
    console.log(packageDir)
    await exec("python3 -m build", {cwd: packageDir})
    // single backslashes get stripped out by the command line so we need to double them
    await runPython(`twine upload ${path.join(packageDir, "dist").replaceAll("\\", "\\\\")}/* -u __token__ -p ${pyPiKey}`)
}
await handlePyPi("concierge-util", "concierge_util", conciergeUtilPyProject)
await handlePyPi("isi-util", "isi_util", isiUtilPyProject)
