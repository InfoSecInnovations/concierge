import path from "node:path";
import AdmZip from "adm-zip";

const zip = new AdmZip();
zip.addLocalFolder(
	path.join(import.meta.dir, "docker_compose"),
	"docker_compose",
	// the installer extracts this zip over the working directory on every launch, so bundling a
	// model configuration from the machine which built it would wipe out the user's own
	(filename) => path.basename(filename) != "my-models.ini",
);
zip.writeZip(path.join(import.meta.dir, "assets", "docker_compose.zip"));
