import AdmZip from "adm-zip";
import path from "node:path"

const zip = new AdmZip()
await zip.addLocalFolderPromise(path.join(import.meta.dir, "docker_compose"), {zipPath: "docker_compose"})
await zip.writeZipPromise(path.join(import.meta.dir, "..", "assets", "docker_compose.zip"), {overwrite: true})