import * as client from "openid-client";

export default () => {
	return client.discovery(
		new URL(
			`https://${process.env.KEYCLOAK_HOST || "localhost"}:8443/realms/shabti/.well-known/openid-configuration`,
		),
		process.env.KEYCLOAK_CLIENT_ID!,
		process.env.KEYCLOAK_CLIENT_SECRET!,
	);
};
