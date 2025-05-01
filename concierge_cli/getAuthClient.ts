import { ConciergeAuthorizationClient } from "concierge-api-client";
import * as openIdClient from "openid-client"
import getOpenIdConfig from "./getOpenIdConfig";

export default async () => {
  // TODO: we need to use the root CA certs rather than disabling verification!
  process.env.NODE_TLS_REJECT_UNAUTHORIZED='0'
  const config = await getOpenIdConfig()
  const token = await openIdClient.clientCredentialsGrant(config)
  const url = process.env.API_URL || `https://${process.env.API_HOST || 'localhost'}:${process.env.API_PORT || '8000'}`
  return new ConciergeAuthorizationClient(url, token, config)
} 