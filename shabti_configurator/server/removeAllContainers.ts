import { $ } from "bun";

export default () =>
	$`docker container rm --force shabti shabti-web llama_cpp opensearch-node1 opensearch-dashboards keycloak postgres tika`;
