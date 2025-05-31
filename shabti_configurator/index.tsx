import { parseArgs } from "node:util";
import AdmZip from "adm-zip";
import { type Subprocess, file } from "bun";
import { $ } from "bun";
import { Hono } from "hono";
import dockerComposeZip from "./assets/docker_compose.zip" with {
	type: "file",
};
import js from "./assets/index.js" with { type: "file" };
import css from "./assets/style.css" with { type: "file" };
import shabtiIsConfigured from "./server/shabtiIsConfigured";
import doInstall from "./server/doInstall";
import doLaunch from "./server/doLaunch";
import dockerIsRunning from "./server/dockerIsRunning";
import { ExistingRemover } from "./server/existingRemover";
import getVersion from "./server/getVersion.js";
import { InstallOptionsForm } from "./server/installOptionsForm";
import { RelaunchForm } from "./server/relaunchForm";
import streamHtml from "./server/streamHtml.js";
import validateInstallForm from "./server/validateInstallForm.js";
import { WebUILink } from "./server/webUiLink.js";

const { values } = parseArgs({
	args: Bun.argv,
	options: {
		"dev-mode": {
			type: "boolean",
		},
	},
	strict: true,
	allowPositionals: true,
});

const devMode = !!values["dev-mode"];

const state: { apiWorker?: Subprocess; webWorker?: Subprocess } = {};

const app = new Hono();

app.get("/style.css", async (c) =>
	c.body(await file(css).text(), 201, {
		"Content-Type": "text/css",
	}),
);
app.get("/index.js", async (c) =>
	c.body(await file(js).text(), 201, {
		"Content-Type": "text/javascript",
	}),
);
app.get("/", async (c) => {
	const dockerStatus = await dockerIsRunning();
	const shabtiIsInstalled = await shabtiIsConfigured();
	return await c.html(
		<html>
			<head>
				<link rel="stylesheet" href="./style.css" />
			</head>
			<body>
				<h1>Shabti Configurator</h1>
				<div id="form_errors" class="error"></div>
				<p>
					This is a utility to install and configure Shabti AI, a tool made by{" "}
					<a
						href="https://www.infosecinnovations.com/"
						target="_blank"
						rel="noreferrer"
					>
						InfoSec Innovations
					</a>
				</p>
				<p>
					Having trouble? Got suggestions for improving Shabti? Head over to our{" "}
					<a
						href="https://github.com/InfoSecInnovations/shabti"
						target="_blank"
						rel="noreferrer"
					>
						GitHub
					</a>
					!
				</p>
				{dockerStatus ? (
					<>
						{shabtiIsInstalled ? (
							<section>
								<h3>Launch Shabti</h3>
								<p>Shabti appears to be configured on this system</p>
								<WebUILink></WebUILink>
								<p>
									If the link above isn't working, try (re)launching using the
									button below.
								</p>
								<p>
									Bear in mind that if you just installed Shabti it can take a
									few minutes before it's up and running.
								</p>
								<RelaunchForm
									devMode={devMode}
									apiIsRunning={!!state.apiWorker}
									webIsRunning={!!state.webWorker}
								></RelaunchForm>
							</section>
						) : null}
						<ExistingRemover></ExistingRemover>
						<section>
							<h3>Install Shabti</h3>
							<InstallOptionsForm devMode={devMode}></InstallOptionsForm>
						</section>
					</>
				) : (
					<section>
						<h3>Docker isn't running, please start it!</h3>
						<p>
							Docker is needed to install and run Shabti. We don't currently
							have a way to integrate it into the installer, so you will have to
							install it yourself.
						</p>
						<p>
							You can find install instructions here:{" "}
							<a href="https://docs.docker.com/engine/install/">
								https://docs.docker.com/engine/install/
							</a>
							. Please note that on Linux you have to follow the instructions
							very precisely otherwise you can end up installing Docker
							incorrectly!
						</p>
						<p>
							If you have already installed it, please launch Docker Desktop or
							start the daemon and this page should display the Shabti
							installation options.
						</p>
					</section>
				)}
			</body>
			<script src="index.js"></script>
		</html>,
	);
});
app.post("/install", (c) =>
	c.req.formData().then((data) => {
		if (!validateInstallForm(data)) return c.redirect("/?err=invalid-form");
		return streamHtml(c, "Installing Shabti", async (stream) => {
			for await (const message of doInstall(data)) {
				await stream.writeln(await (<p>{message}</p>));
			}
		});
	}),
);
app.post("/remove", (c) =>
	c.req.formData().then((data) => {
		const service = data.get("service");
		if (service == "shabti")
			return streamHtml(c, "Removing Shabti API service", async (_) => {
				await $`docker container rm --force shabti`;
			});
		if (service == "shabti-web")
			return streamHtml(c, "Removing Shabti Web UI service", async (_) => {
				await $`docker container rm --force shabti-web`;
			});
		if (service == "ollama")
			return streamHtml(c, "Removing Ollama service", async (_) => {
				await $`docker container rm --force ollama`;
				await $`docker volume rm --force shabti_ollama`;
			});
		if (service == "opensearch")
			return streamHtml(c, "Removing OpenSearch service", async (_) => {
				await $`docker container rm --force opensearch-node1`;
				await $`docker volume rm --force shabti_opensearch-data1`;
			});
		if (service == "keycloak")
			return streamHtml(c, "Removing Keycloak service", async (_) => {
				await $`docker container rm --force keycloak postgres`;
				await $`docker volume rm --force shabti_postgres_data`;
			});
		return c.html(<p>Invalid service name was provided!</p>);
	}),
);
app.post("/launch", (c) =>
	c.req.formData().then((data) =>
		streamHtml(c, "Launching Shabti", async (stream) => {
			for await (const message of doLaunch(data, state)) {
				await stream.writeln(await (<p>{message}</p>));
			}
		}),
	),
);

console.log("Shabti Configurator");
console.log(`${getVersion()}\n`);

// we need the compose files to be available outside of the executable bundle so the shell can use them
const buf = await file(dockerComposeZip).arrayBuffer();
const zip = new AdmZip(Buffer.from(buf));
zip.extractAllTo(".", true);
console.log("Extracted docker compose files.\n");

Bun.serve({ ...app, idleTimeout: 0 });
console.log("visit http://localhost:3000 to install or manage Shabti");
