import type { Context } from "hono";
import { stream } from 'hono/streaming'
import type { StreamingApi } from "hono/utils/stream";

export default (c: Context, startMessage: string, func: (stream: StreamingApi) => Promise<void>) => {
    const resp = stream(c, async stream => {
    await stream.writeln(await <><head>
        <meta http-equiv="Refresh" content="0; URL=/" />
    </head><p>{startMessage}</p></>)
    await func(stream)
    await stream.writeln("Done! returning to main page!")
    })
    resp.headers.set('Content-Type', 'text/html; charset=UTF-8')
    resp.headers.set('Transfer-Encoding', 'chunked')
    return resp
}