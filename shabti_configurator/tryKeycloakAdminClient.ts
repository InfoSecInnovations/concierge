import keycloakAdminClient from "./server/keycloakAdminClient";

const client = await keycloakAdminClient();

console.log(
	await client.clients.findOne({ id: "7a3ec428-36f2-49c4-91b1-8288dc44acb0" }),
);
