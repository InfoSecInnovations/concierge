import AdmZip from "adm-zip";
import path from "node:path"

const zip = new AdmZip()
zip.addLocalFolder(path.join(import.meta.dir, "docker_compose"), "docker_compose")
zip.writeZip(path.join(import.meta.dir, "..", "assets", "docker_compose.zip"))