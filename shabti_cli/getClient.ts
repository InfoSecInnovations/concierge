import { ConciergeClient } from "shabti-api-client";

export default () => {
	const url =
		process.env.API_URL ||
		`http://${process.env.API_HOST || "localhost"}:${process.env.API_PORT || "8000"}`;
	return new ConciergeClient(url);
};
