import * as openIdClient from "openid-client";
import getOpenIdConfig from "./getOpenIdConfig";

export default async () => {
	// TODO: we need to use the root CA certs rather than disabling verification!
	process.env.NODE_TLS_REJECT_UNAUTHORIZED = "0";
	const config = await getOpenIdConfig();
	return await openIdClient.clientCredentialsGrant(config);
};
