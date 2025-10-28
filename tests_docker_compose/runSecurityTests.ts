import { $ } from "bun";
import createCertificates from "../shabti_configurator/server/createCertificates";
import getKeycloakClientSecret from "../shabti_configurator/server/getKeycloakClientSecret";
import path from "path";
import * as dotenv from "dotenv";
import nukeExisting from "./nukeExisting";

export default async () => {
	console.log(`
  -----------------------------------------------------
    RUNNING TESTS FOR SECURITY ENABLED INSTANCE...
  -----------------------------------------------------
  `);

	dotenv.config({ path: "security-enabled-env", override: true, quiet: true });
	await nukeExisting();
	await createCertificates("./self_signed_certificates");
	await Bun.write(
		".env",
		`
  ROOT_CA=${path.resolve(path.join(import.meta.dir, "self_signed_certificates", "root-ca.pem"))}
  KEYCLOAK_CERT=${path.resolve(path.join(import.meta.dir, "self_signed_certificates", "keycloak-cert.pem"))}
  KEYCLOAK_CERT_KEY=${path.resolve(path.join(import.meta.dir, "self_signed_certificates", "keycloak-key.pem"))}
  API_CERT=${path.resolve(path.join(import.meta.dir, "self_signed_certificates", "shabti-cert.pem"))}
  API_KEY=${path.resolve(path.join(import.meta.dir, "self_signed_certificates", "shabti-key.pem"))}
  `,
	);
	dotenv.config({
		path: ["security-enabled-env", ".env"],
		override: true,
		quiet: true,
	}); // the local env seems to get applied to the Docker commands so it's important we keep it updated
	console.log(
		"building Docker Compose... (can take some time if there are updates to the dependencies)",
	);
	await $`docker compose --env-file security-enabled-env --env-file .env -f ./docker-compose-pytest.yml build`.quiet();
	await $`docker compose --env-file security-enabled-env --env-file .env -f ../shabti_configurator/docker_compose/docker-compose-launch-keycloak.yml up -d`.quiet();
	console.log("Getting Keycloak Client Secret...");
	const secret = await getKeycloakClientSecret();
	console.log("Got Keycloak Client Secret.");
	await Bun.write(
		".env",
		`
  KEYCLOAK_CLIENT_SECRET=${secret}
  ROOT_CA=${path.resolve(path.join(import.meta.dir, "self_signed_certificates", "root-ca.pem"))}
  KEYCLOAK_CERT=${path.resolve(path.join(import.meta.dir, "self_signed_certificates", "keycloak-cert.pem"))}
  KEYCLOAK_CERT_KEY=${path.resolve(path.join(import.meta.dir, "self_signed_certificates", "keycloak-key.pem"))}
  API_CERT=${path.resolve(path.join(import.meta.dir, "self_signed_certificates", "shabti-cert.pem"))}
  API_KEY=${path.resolve(path.join(import.meta.dir, "self_signed_certificates", "shabti-key.pem"))}
  `,
	);
	dotenv.config({
		path: ["security-enabled-env", ".env"],
		override: true,
		quiet: true,
	}); // the local env seems to get applied to the Docker commands so it's important we keep it updated
	await $`docker compose --env-file security-enabled-env --env-file .env -f ./docker-compose-pytest.yml build`.quiet();
	await $`docker compose --env-file security-enabled-env --env-file .env -f ./docker-compose-pytest.yml up -d`.quiet();
	await $`docker exec shabti uv run -m add_keycloak_demo_users`.quiet();
	console.log(`
  ____________RUNNING PYTHON TESTS______________
  `);
	await $`docker compose --env-file security-enabled-env --env-file .env -f ./docker-compose-pytest.yml up --attach shabti`;
	process.env.NODE_TLS_REJECT_UNAUTHORIZED = "0";
	console.log(
		"building Docker Compose... (can take some time if there are updates to the dependencies)",
	);
	await $`docker compose --env-file security-enabled-env --env-file .env -f ./docker-compose-client-test.yml build`.quiet();
	await $`docker compose --env-file security-enabled-env --env-file .env -f ./docker-compose-client-test.yml up --attach shabti-client`;
	// launch API
	await $`docker compose --env-file security-enabled-env --env-file .env build`.quiet();
	console.log(
		"building Docker Compose... (can take some time if there are updates to the dependencies)",
	);
	await $`docker compose --env-file security-enabled-env --env-file .env up -d`;
	console.log(`
  __________RUNNING NODE TESTS___________
  `);
	console.log("waiting for API service to launch...");
	while (true) {
		try {
			await fetch("https://localhost:15131");
			break;
		} catch {
			continue;
		}
	}
	await $`bun test --reporter=junit --reporter-outfile=./tests_docker_compose/test_results/bun_security_enabled.xml`
		.cwd("..")
		.env({ ...process.env, FORCE_COLOR: "1" });
};
