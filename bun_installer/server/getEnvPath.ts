import path from "node:path"

export default () => path.join(import.meta.dir, "..", "docker_compose", ".env")