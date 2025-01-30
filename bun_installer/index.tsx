import { Hono } from "hono"
import { InstallOptionsForm } from "./server/installOptionsForm"
import doInstall from "./server/doInstall"
import dockerIsRunning from "./server/dockerIsRunning"
import conciergeIsConfigured from "./server/conciergeIsConfigured"
import { RelaunchForm } from "./server/relaunchForm"
import doLaunch from "./server/doLaunch"
import { ExistingRemover } from "./server/existingRemover"
import { stream } from 'hono/streaming'

const app = new Hono()

app.get('/', async c => {
  const dockerStatus = await dockerIsRunning()
  const conciergeIsInstalled = await conciergeIsConfigured()
  return await c.html(
  <html>
    <head>
      <link rel="stylesheet" href="./style.css" />     
    </head>
    <body>
      <h1>Concierge Configurator</h1>
      <p>This is a utility to install and configure Concierge Data AI, a tool made by <a href="https://www.infosecinnovations.com/">InfoSec Innovations</a></p>
      {dockerStatus ? <>
        {conciergeIsInstalled ? <>
          <h3>Launch Concierge</h3>
          <p>Concierge appears to be configured on this system. You can (re)launch here if needed.</p>
          <RelaunchForm></RelaunchForm>
        </> : null}
        <ExistingRemover></ExistingRemover>
        <h3>Install Concierge</h3>
        <InstallOptionsForm></InstallOptionsForm>
      </> : <>
        <h3>Docker isn't running, please start it!</h3>
        <p>Docker is needed to install and run Concierge. We don't currently have a way to integrate it into the installer, so you will have to install it yourself.</p>
        <p>You can find install instructions here: <a href="https://docs.docker.com/engine/install/">https://docs.docker.com/engine/install/</a>. Please note that on Linux you have to follow the instructions very precisely otherwise you can end up installing Docker incorrectly!</p>
        <p>If you have already installed it, please launch Docker Desktop or start the daemon and this page should display the Concierge installation options.</p>
      </>}
    </body> 
    <script src="index.js"></script>  
  </html>)
})
app.post("/install", c => c.req.formData()
  .then(data => {
    const resp = stream(c, async stream => {
      await stream.writeln(await <head>
        <meta http-equiv="Refresh" content="0; URL=/" />
      </head>)
      for await (const message of doInstall(data)) {
        await stream.writeln(await <p>{message}</p>)
      }
    })
    resp.headers.set('Content-Type', 'text/html; charset=UTF-8')
    resp.headers.set('Transfer-Encoding', 'chunked')
    return resp
  })
)
app.post("/launch", c => c.req.formData()
  .then(data => doLaunch(data))
  .then(() => c.redirect("/"))
)

console.log("Concierge Configurator")
console.log(process.env.npm_package_version)
Bun.serve({...app, idleTimeout: 0})