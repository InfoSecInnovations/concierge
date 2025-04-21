import * as envfile from "envfile"
import getEnvPath from "./getEnvPath"

export const WebUILink = async () => {
    const envs = envfile.parse(await Bun.file(getEnvPath()).text())
    const url = `${envs.CONCIERGE_SECURITY_ENABLED == 'True' ? 'https' : 'http'}://${envs.WEB_HOST}:${envs.WEB_PORT}`
    return (<p>If Concierge is already running you will find the web UI here: <a href={url} target="_blank">{url}</a></p>)
}