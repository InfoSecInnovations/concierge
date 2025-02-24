import { $ } from "bun"
import packageJson from "./package.json"

console.log("Concierge release publisher\n")
let version = null
while (!version) {
    version = prompt("Input new Concierge version:")
}
packageJson.version = version
await Bun.write("./package.json", JSON.stringify(packageJson, undefined, "\t"))
await $`git add -A`
await $`git commit -m 'increment version to ${version}'`
