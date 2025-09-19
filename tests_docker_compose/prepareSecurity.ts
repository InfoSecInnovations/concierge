import { $ } from "bun";
import createCertificates from "../shabti_configurator/server/createCertificates";
import getKeycloakClientSecret from "../shabti_configurator/server/getKeycloakClientSecret";

await createCertificates("./self_signed_certificates");
await $`docker compose --env-file security-enabled-env -f ../shabti_configurator/docker_compose/docker-compose-launch-keycloak.yml up -d`;
console.log("Getting Keycloak Client Secret...");
const secret = await getKeycloakClientSecret();
console.log("Got Keycloak Client Secret.");
await Bun.write(".env", `KEYCLOAK_CLIENT_SECRET=${secret}`);
await $`docker compose --env-file security-enabled-env build`;
await $`docker compose --env-file security-enabled-env up -d`;
await $`docker exec -d shabti uv run add_keycloak_demo_users`;
