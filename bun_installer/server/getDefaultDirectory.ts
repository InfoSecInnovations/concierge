import os from "node:os"

export default () => {
    if (os.platform() == "win32") return process.env.PROGRAMDATA
    return "/opt"
}