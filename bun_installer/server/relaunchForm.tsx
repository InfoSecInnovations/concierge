import * as envfile from "envfile"
import getEnvPath from "./getEnvPath"

export const RelaunchForm = async () => {
    const envs = envfile.parse(await Bun.file(getEnvPath()).text())
    return (
        <form action="/launch" method="post">
            <p>
                <input type="checkbox" id="use_gpu" name="use_gpu" checked={envs.OLLAMA_SERVICE=="ollama-gpu"}></input>
                <label for="use_gpu">Enable GPU Acceleration</label>
            </p>
            <button type="submit">Launch Concierge</button>
        </form>
    )
}