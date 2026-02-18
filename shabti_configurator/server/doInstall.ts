import crypto from "node:crypto";
import path from "node:path";
import { $ } from "bun";
import * as envfile from "envfile";
// import configurePlaywright from "./configurePlaywright";
import configurePreCommit from "./configurePreCommit";
import createCertificates from "./createCertificates";
import { keycloakExists } from "./dockerItemsExist";
import getEnvPath from "./getEnvPath";
import logMessage from "./logMessage";
import createVenv from "./createVenv";
import getKeycloakClientSecret from "./getKeycloakClientSecret";
import getCurrentVersion from "./getCurrentVersion";

export default async function* (
	options: FormData,
	selectedVersion: string,
	defaultVersion: string,
	installVenv = true,
) {
	const environment =
		options.get("dev_mode")?.toString() == "True"
			? "development"
			: "production";
	// we keep track of the environment variables so we can write to the .env file and the process environment as needed
	const envs: { [key: string]: string } = {};
	const updateEnv = () => {
		Object.entries(envs).forEach(([key, value]) => (process.env[key] = value));
		return Bun.write(getEnvPath(), envfile.stringify(envs));
	};
	envs.WEB_HOST = options.get("web-host")?.toString() || "localhost";
	envs.WEB_PORT = options.get("web-port")?.toString() || "15130";
	envs.API_HOST = options.get("api-host")?.toString() || "localhost";
	envs.API_PORT = options.get("api-port")?.toString() || "15131";
	const securityLevel = options.get("security_level")?.toString();
	if (securityLevel && securityLevel != "none") {
		yield logMessage("configuring security...");
		envs.SHABTI_SECURITY_ENABLED = "True";
		envs.SHABTI_SERVICE = "shabti-enable-security";
		envs.SHABTI_WEB_SERVICE = "shabti-web-enable-security";
		const certDir = path.resolve("self_signed_certificates");
		await createCertificates(certDir);
		envs.ROOT_CA = path.join(certDir, "root-ca.pem");
		envs.KEYCLOAK_CERT = path.join(certDir, "keycloak-cert.pem");
		envs.KEYCLOAK_CERT_KEY = path.join(certDir, "keycloak-key.pem");
		envs.API_CERT = path.join(certDir, "shabti-cert.pem");
		envs.API_KEY = path.join(certDir, "shabti-key.pem");
		envs.WEB_CERT = path.join(certDir, "shabti-web-cert.pem");
		envs.WEB_KEY = path.join(certDir, "shabti-web-key.pem");
		yield logMessage("configured TLS certificates.");
		if (!(await keycloakExists())) {
			const keycloakPassword = options.get("keycloak_password")?.toString();
			// TODO: create error type for this
			if (!keycloakPassword)
				throw new Error("Keycloak admin password is invalid!");
			// TODO: validate password strength
			// in case we have old postgres data we should remove it to avoid mismatches
			await $`docker volume rm --force shabti_postgres_data`.quiet();
			envs.KEYCLOAK_INITIAL_ADMIN_PASSWORD = keycloakPassword;
			const postgresPassword = crypto.randomBytes(25).toString("hex");
			// TODO: validate password strength
			envs.POSTGRES_DB_PASSWORD = postgresPassword;
			updateEnv();
			yield logMessage(
				"getting OpenID credentials from Keycloak service. This can take a few minutes!",
			);
			const keycloakComposeFile = path.join(
				"docker_compose",
				"docker-compose-launch-keycloak.yml",
			);
			// update the keycloak image otherwise it can get overwritten when we launch everything below
			await $`docker compose -f ${keycloakComposeFile} pull`;
			await $`docker compose -f ${keycloakComposeFile} up -d`;
			envs.KEYCLOAK_CLIENT_ID = "shabti-auth";
			envs.KEYCLOAK_CLIENT_SECRET = await getKeycloakClientSecret();
			yield logMessage("got Keycloak credentials.");
		}
		envs.KEYCLOAK_SERVICE_FILE = "docker-compose-keycloak.yml";
	} else {
		envs.SHABTI_SERVICE = "shabti-disable-security";
		envs.SHABTI_WEB_SERVICE = "shabti-web";
		envs.SHABTI_SECURITY_ENABLED = "False";
		envs.KEYCLOAK_SERVICE_FILE = "docker-compose-blank.yml";
	}
	envs.ENVIRONMENT = environment;
	envs.SHABTI_VERSION =
		selectedVersion == "local"
			? (await getCurrentVersion()) || defaultVersion
			: selectedVersion;
	envs.SHABTI_LOCAL_VERSION = selectedVersion == "local" ? "True" : "False";
	envs.SHABTI_COMPUTE = options.has("use_gpu") ? "cuda" : "cpu";
	if (securityLevel == "demo") envs.IS_SECURITY_DEMO = "True";
	if (options.has("activity_logging")) {
		envs.SHABTI_BASE_SERVICE = "shabti-logging";
		envs.SHABTI_LOG_DIR = options.get("logging_location")?.toString() || "";
	} else {
		envs.SHABTI_BASE_SERVICE = "shabti";
	}

	await updateEnv();
	yield logMessage(
		"launching Docker containers. This can take quite a long time if this is your first launch or updates have been released to the Docker images...",
	);
	if (environment == "development") {
		await $`docker compose -f ./docker_compose/docker-compose-dev.yml pull`;
		await $`docker compose -f ./docker_compose/docker-compose-dev.yml build`;
		await $`docker compose -f ./docker_compose/docker-compose-dev.yml up -d`;
		if (installVenv) {
			// if we're running the install for automated testing we assume the venv is already configured, so we want to skip this step
			yield logMessage(
				"configuring Python environments. This can take some time if you have slow internet...",
			);
			await createVenv();
			await configurePreCommit();
		}
	} else {
		await $`docker compose -f ./docker_compose/docker-compose.yml pull`;
		await $`docker compose -f ./docker_compose/docker-compose.yml up -d`;
	}
	if (securityLevel == "demo") {
		yield logMessage("adding demo users");
		await $`docker exec shabti uv run -m add_keycloak_demo_users`;
	}
	yield logMessage("waiting for Ollama to come online...");
	// while ollama is failing to fetch or returning a non 200 status code, we keep looping
	while (
		await fetch("http://localhost:11434/").then(
			(res) => res.status != 200,
			() => true,
		)
	) {}
	yield logMessage(
		"pulling language model. This can take quite a long time if you haven't downloaded the model before.",
	);
	// TODO use options.get("language_model")
	await $`docker exec ollama ollama pull mistral`;
	if (environment == "development") {
		// in the development environment we stop the containers as the expectation is that they will be run in watch mode
		await $`docker compose -f ./docker_compose/docker-compose-dev.yml stop`;
	}
	console.log("Installation done\n");
}
