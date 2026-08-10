import getKeycloakAdminClient from "./keycloakAdminClient";

// the realm is imported into the postgres volume the first time Keycloak boots and never
// again, so the redirect URIs it was templated with go stale when the web host or port change.
// Updating the client applies the change without recreating the realm, which would lose every
// user and regenerate the client secret the rest of the stack is configured with
const shabtiAuthId = "7a3ec428-36f2-49c4-91b1-8288dc44acb0"; // pinned by shabti-realm.json

export default async (webHost: string, webPort: string) => {
	const client = await getKeycloakAdminClient();
	// the same entries the realm file is templated with, so an updated client matches a freshly
	// imported one. Note that a browser omits the port from the origin it sends when it's the
	// default for the scheme, so ports 443 and 80 won't match these
	await client.clients.update(
		{ id: shabtiAuthId },
		{
			// Keycloak treats this one as an absolute value rather than a patch, so leaving it
			// out disables authorization services and deletes the resource server along with
			// every collection resource in it. Every other field falls back to its stored value
			authorizationServicesEnabled: true,
			redirectUris: [
				`http://${webHost}:${webPort}/callback`,
				`https://${webHost}:${webPort}/callback`,
				"http://127.0.0.1:8000/*",
			],
			webOrigins: [
				`https://${webHost}:${webPort}`,
				`http://${webHost}:${webPort}`,
				"http://127.0.0.1:8000",
			],
		},
	);
};
