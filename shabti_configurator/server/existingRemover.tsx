import { dockerItemExists } from "./dockerItemsExist";

export const ExistingRemover = async () => {
	const [
		shabtiExists,
		ollamaExists,
		keycloakExists,
		opensearchExists,
		shabtiWebExists,
	] = await Promise.all([
		dockerItemExists("shabti", "container"),
		Promise.all([
			dockerItemExists("ollama", "container"),
			dockerItemExists("shabti_ollama", "volume"),
		]).then((res) => res.some((exists) => exists)),
		Promise.all([
			dockerItemExists("keycloak", "container"),
			dockerItemExists("postgres", "container"),
			dockerItemExists("shabti_postgres_data", "volume"),
		]).then((res) => res.some((exists) => exists)),
		Promise.all([
			dockerItemExists("opensearch", "container"),
			dockerItemExists("shabti_opensearch-data1", "volume"),
		]).then((res) => res.some((exists) => exists)),
		dockerItemExists("shabti-web", "container"),
	]);
	if (
		!shabtiExists &&
		!ollamaExists &&
		!keycloakExists &&
		!opensearchExists &&
		!shabtiWebExists
	)
		return <></>;
	return (
		<section>
			<h3>Remove existing Docker services (containers and related volumes)</h3>
			<p>
				This can help you if your installation appears to be broken or you want
				to create a fresh install.
			</p>
			<p>
				If you're switching between having security enabled and disabled or
				vice-versa, it's strongly recommended that you remove all existing
				containers except for Ollama.
			</p>
			<p>
				Be aware that if you remove Ollama you will have to redownload the LLM
				models which are quite large.
			</p>
			<form action="/remove" method="post">
				{shabtiExists && (
					<button type="submit" name="service" value="shabti">
						Remove Shabti API service
					</button>
				)}
				{shabtiWebExists && (
					<button type="submit" name="service" value="shabti-web">
						Remove Shabti Web UI service
					</button>
				)}
				{ollamaExists && (
					<button type="submit" name="service" value="ollama">
						Remove Ollama service
					</button>
				)}
				{keycloakExists && (
					<button type="submit" name="service" value="keycloak">
						Remove Keycloak service
					</button>
				)}
				{opensearchExists && (
					<button type="submit" name="service" value="opensearch">
						Remove OpenSearch service
					</button>
				)}
			</form>
		</section>
	);
};
