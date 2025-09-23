import { $ } from "bun";
import createCertificates from "../shabti_configurator/server/createCertificates";
import getKeycloakClientSecret from "../shabti_configurator/server/getKeycloakClientSecret";
import path from "path";
import * as dotenv from "dotenv";

const nukeExisting = async () => {
	await $`docker container rm --force opensearch-node1`.quiet();
	await $`docker volume rm --force shabti_opensearch-data1`.quiet();
	await $`docker container rm --force keycloak postgres`.quiet();
	await $`docker volume rm --force shabti_postgres_data`.quiet();
};

console.log(`
-----------------------------------------------------
   RUNNING TESTS FOR SECURITY DISABLED INSTANCE...
-----------------------------------------------------
`);

dotenv.config({ path: "security-disabled-env", override: true });
await nukeExisting();
await $`docker compose --env-file security-disabled-env build`.quiet();
await $`docker compose --env-file security-disabled-env up --attach shabti`;

console.log(`
-----------------------------------------------------
   RUNNING TESTS FOR SECURITY ENABLED INSTANCE...
-----------------------------------------------------
`);

dotenv.config({ path: "security-enabled-env", override: true });
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
dotenv.config({ path: ["security-enabled-env", ".env"], override: true }); // the local env seems to get applied to the Docker commands so it's important we keep it updated
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
dotenv.config({ path: ["security-enabled-env", ".env"], override: true }); // the local env seems to get applied to the Docker commands so it's important we keep it updated
await $`docker compose --env-file security-enabled-env --env-file .env build`.quiet();
await $`docker compose --env-file security-enabled-env --env-file .env up -d`.quiet();
await $`docker exec shabti uv run -m add_keycloak_demo_users`.quiet();
await $`docker compose --env-file security-enabled-env --env-file .env up --attach shabti`;
