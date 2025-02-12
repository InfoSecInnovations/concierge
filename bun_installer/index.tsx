import { Hono } from "hono"
import { InstallOptionsForm } from "./server/installOptionsForm"
import doInstall from "./server/doInstall"
import dockerIsRunning from "./server/dockerIsRunning"
import conciergeIsConfigured from "./server/conciergeIsConfigured"
import { RelaunchForm } from "./server/relaunchForm"
import doLaunch from "./server/doLaunch"
import { ExistingRemover } from "./server/existingRemover"
import css from "./assets/style.css" with {type: "file"}
import js from "./assets/index.js" with {type: "file"}
import { file } from "bun"
import validateInstallForm from "./server/validateInstallForm.js"
import { $ } from "bun"
import streamHtml from "./server/streamHtml.js"
import { WebUILink } from "./server/webUiLink.js"
import getVersion from "./server/getVersion.js"

const app = new Hono()

app.get('/style.css', async c => c.body(await file(css).text(), 201, {
  'Content-Type': "text/css"
}))
app.get('/index.js', async c => c.body(await file(js).text(), 201, {
  'Content-Type': "text/javascript"
}))
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
      <p>This is a utility to install and configure Concierge Data AI, a tool made by <a href="https://www.infosecinnovations.com/" target="_blank">InfoSec Innovations</a></p>
      {dockerStatus ? <>
        {conciergeIsInstalled ? <section>
          <h3>Launch Concierge</h3>
          <p>Concierge appears to be configured on this system</p>
          <WebUILink></WebUILink>
          <p>If the link above isn't working, try (re)launching using the button below.</p>
          <p>Bear in mind that if you just installed Concierge it can take a few minutes before it's up and running.</p>
          <RelaunchForm></RelaunchForm>
        </section> : null}
        <ExistingRemover></ExistingRemover>
        <section>
          <h3>Install Concierge</h3>
          <InstallOptionsForm></InstallOptionsForm>
        </section>
      </> : <section>
        <h3>Docker isn't running, please start it!</h3>
        <p>Docker is needed to install and run Concierge. We don't currently have a way to integrate it into the installer, so you will have to install it yourself.</p>
        <p>You can find install instructions here: <a href="https://docs.docker.com/engine/install/">https://docs.docker.com/engine/install/</a>. Please note that on Linux you have to follow the instructions very precisely otherwise you can end up installing Docker incorrectly!</p>
        <p>If you have already installed it, please launch Docker Desktop or start the daemon and this page should display the Concierge installation options.</p>
      </section>}
    </body> 
    <script src="index.js"></script>
  </html>)
})
app.post("/install", c => c.req.formData()
  .then(data => {
    if (!validateInstallForm(data)) return c.redirect("/?err=invalid-form")
    return streamHtml(c, "Installing Concierge", async stream => {
      for await (const message of doInstall(data)) {
        await stream.writeln(await <p>{message}</p>)
      }
    })
  })
)
app.post("/remove_concierge", c => streamHtml(c, "Removing Concierge service", async _ => {
  await $`docker container rm --force concierge`
}))
app.post("/remove_ollama", c => streamHtml(c, "Removing Ollama service", async _ => {
  await $`docker container rm --force ollama`
  await $`docker volume rm --force concierge_ollama`
}))
app.post("/remove_opensearch", c => streamHtml(c, "Removing OpenSearch service", async _ => {
  await $`docker container rm --force opensearch-node1`
  await $`docker volume rm --force concierge_opensearch-data1`
}))
app.post("/remove_keycloak", c => streamHtml(c, "Removing Keycloak service", async _ => {
  await $`docker container rm --force keycloak postgres`
  await $`docker volume rm --force concierge_postgres_data`
}))
app.post("/launch", c => c.req.formData()
  .then(data => streamHtml(c, "Launching Concierge", async _ => await doLaunch(data)))
)

console.log("Concierge Configurator")
console.log(`${getVersion()}\n`)
console.log("visit http://localhost:3000 to install or manage Concierge")
Bun.serve({...app, idleTimeout: 0})