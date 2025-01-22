import { Hono } from "hono"
import { InstallOptionsForm } from "./server/installOptionsForm"
import doInstall from "./server/doInstall"

const app = new Hono()

app.get('/', (c) => {
  return c.html(
  <html>
    <head>
      <link rel="stylesheet" href="./style.css" />     
    </head>
    <body>
      <h1>Concierge Configurator</h1>
      <p>This is a utility to install and configure Concierge Data AI, a tool made by <a href="https://www.infosecinnovations.com/">InfoSec Innovations</a></p>
      <h3>TODO: there will be an option to launch Concierge here</h3>
      <h3>TODO: there will be an option to remove an existing installation here</h3>
      <h3>Install Concierge</h3>
      <InstallOptionsForm></InstallOptionsForm>
    </body> 
    <script src="index.js"></script>  
  </html>)
})
app.post("/install", c => c.req.formData()
  .then(data => doInstall(data))
  .then(() => c.redirect("/"))
)

export default app