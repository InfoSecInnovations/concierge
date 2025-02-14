import path from "node:path"

Bun.spawn(["Scripts\\python", "-m", "dev_launcher"], {cwd: path.resolve("..")})