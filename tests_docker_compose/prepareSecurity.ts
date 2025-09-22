import { $ } from "bun";
import createCertificates from "../shabti_configurator/server/createCertificates";
import getKeycloakClientSecret from "../shabti_configurator/server/getKeycloakClientSecret";
import path from "path";

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
await $`docker compose --env-file security-enabled-env --env-file .env -f ../shabti_configurator/docker_compose/docker-compose-launch-keycloak.yml up -d`;
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
await $`docker compose --env-file security-enabled-env --env-file .env build`;
await $`docker compose --env-file security-enabled-env --env-file .env up -d`;
await $`docker exec shabti uv run -m add_keycloak_demo_users`;
await $`docker compose stop`;
