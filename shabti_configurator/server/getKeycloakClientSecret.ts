import KcAdminClient from "@keycloak/keycloak-admin-client";

export default async () => {
	process.env.NODE_TLS_REJECT_UNAUTHORIZED = "0";
	// keep trying this until keycloak is up
	while (true) {
		try {
			const kcClient = new KcAdminClient({
				baseUrl: "https://localhost:8443",
			});
			await kcClient.auth({
				username: "admin",
				password: process.env.KEYCLOAK_INITIAL_ADMIN_PASSWORD,
				grantType: "password",
				clientId: "admin-cli",
			});
			const secret = await kcClient.clients.getClientSecret({
				id: "7a3ec428-36f2-49c4-91b1-8288dc44acb0",
				realm: "shabti",
			});
			return secret.value!;
		} catch (error) {
			continue;
		}
	}
};
