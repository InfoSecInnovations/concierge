import { Hono } from "hono"
import { InstallOptionsForm } from "./server/installOptionsForm"

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
      <InstallOptionsForm></InstallOptionsForm>
    </body> 
    <script src="index.js"></script>  
  </html>)
})
app.post("/install", c => {
  // TODO: install stuff
  return c.json({success: true}, 200)
})

export default app