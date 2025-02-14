import * as envfile from "envfile"
import getEnvPath from "./getEnvPath"

export const RelaunchForm = async (props: {devMode: boolean, isRunning?: boolean}) => {
    const envs = envfile.parse(await Bun.file(getEnvPath()).text())
    return (
        <form action="/launch" method="post">
            <p>
                <input type="checkbox" id="launch_with_gpu" name="use_gpu" checked={envs.OLLAMA_SERVICE=="ollama-gpu"}></input>
                <label for="launch_with_gpu">Enable GPU Acceleration</label>
            </p>
            <button type="submit">Launch Concierge</button>
            {props.devMode && <>
                <button type="submit" name="environment" value="local">Launch Local Code (Docker)</button>
                {props.isRunning ? 
                <button type="submit" name="environment" value="stop_development">Stop Local Code (Python)</button> :
                <button type="submit" name="environment" value="development">Launch Local Code (Python)</button>}
            </>}
        </form>
    )
}