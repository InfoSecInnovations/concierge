// The tests run in a container on the compose network, so the API is not on localhost. Same
// resolution order as shabti_cli/getClient.ts, with the scheme depending on whether the instance
// under test has security enabled.
export default (scheme: "http" | "https") =>
	process.env.API_URL ||
	`${scheme}://${process.env.API_HOST || "localhost"}:${process.env.API_PORT || "15131"}`;
