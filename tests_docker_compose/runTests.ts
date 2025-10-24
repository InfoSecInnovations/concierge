import { $ } from "bun";
import * as dotenv from "dotenv";
import nukeExisting from "./nukeExisting";
import runSecurityTests from "./runSecurityTests";

console.log(`
-----------------------------------------------------
   RUNNING TESTS FOR SECURITY DISABLED INSTANCE...
-----------------------------------------------------
`);

dotenv.config({ path: "security-disabled-env", override: true, quiet: true });
await nukeExisting();
console.log(
	"building Docker Compose... (can take some time if there are updates to the dependencies)",
);
await $`docker compose --env-file security-disabled-env -f ./docker-compose-pytest.yml build`.quiet();
console.log(`
____________RUNNING PYTHON TESTS______________
`);
await $`docker compose --env-file security-disabled-env -f ./docker-compose-pytest.yml up --attach shabti`;
console.log(
	"building Docker Compose... (can take some time if there are updates to the dependencies)",
);
await $`docker compose --env-file security-disabled-env -f ./docker-compose-client-test.yml build`.quiet();
await $`docker compose --env-file security-disabled-env -f ./docker-compose-client-test.yml up --attach shabti-client`;
// launch API
await $`docker compose --env-file security-disabled-env build`.quiet();
await $`docker compose --env-file security-disabled-env up -d`;
console.log(`
__________RUNNING NODE CLIENT TESTS___________
`);
console.log("waiting for API service to launch...");
while (true) {
	try {
		await fetch("http://localhost:15131");
		break;
	} catch {
		continue;
	}
}
await $`bun test`.cwd("..").env({ ...process.env, FORCE_COLOR: "1" });

await runSecurityTests();
