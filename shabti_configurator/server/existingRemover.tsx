import { dockerItemExists } from "./dockerItemsExist";

export const ExistingRemover = async () => {
	const [
		shabtiExists,
		llamaCppExists,
		keycloakExists,
		opensearchExists,
		shabtiWebExists,
		tikaExists,
	] = await Promise.all([
		dockerItemExists("shabti", "container"),
		Promise.all([
			dockerItemExists("llama_cpp", "container"),
			dockerItemExists("shabti_llama_cpp", "volume"),
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
		dockerItemExists("tika", "container"),
	]);
	if (
		!shabtiExists &&
		!llamaCppExists &&
		!keycloakExists &&
		!opensearchExists &&
		!shabtiWebExists &&
		!tikaExists
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
				containers except for Llama.cpp.
			</p>
			<p>
				Be aware that if you remove Llama.cpp you will have to redownload the
				LLM models which are quite large.
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
				{llamaCppExists && (
					<button type="submit" name="service" value="llama_cpp">
						Remove Llama.cpp service
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
				{tikaExists && (
					<button type="submit" name="service" value="tika">
						Remove Apache Tika service
					</button>
				)}
			</form>
		</section>
	);
};
