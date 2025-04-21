import { dockerItemExists } from "./dockerItemsExist"

export const ExistingRemover = async () => {
    const [conciergeExists, ollamaExists, keycloakExists, opensearchExists, conciergeWebExists] = await Promise.all([
        dockerItemExists("concierge", "container"),
        Promise.all([
            dockerItemExists("ollama", "container"),
            dockerItemExists("concierge_ollama", "volume")
        ]).then(res => res.some(exists => exists)),
        Promise.all([
            dockerItemExists("keycloak", "container"),
            dockerItemExists("postgres", "container"),
            dockerItemExists("concierge_postgres_data", "volume")
        ]).then(res => res.some(exists => exists)),
        Promise.all([
            dockerItemExists("opensearch", "container"),
            dockerItemExists("concierge_opensearch-data1", "volume")
        ],).then(res => res.some(exists => exists)),
        dockerItemExists("concierge_web", "container")
    ])
    if (!conciergeExists && !ollamaExists && !keycloakExists && !opensearchExists && !conciergeWebExists) return <></>
    return (<section>
        <h3>Remove existing Docker services (containers and related volumes)</h3>
        <p>This can help you if your installation appears to be broken or you want to create a fresh install.</p>
        <p>If you're switching between having security enabled and disabled or vice-versa, it's strongly recommended that you remove all existing containers except for Ollama.</p>
        <p>Be aware that if you remove Ollama you will have to redownload the LLM models which are quite large.</p>
        <form action="/remove" method="post">
            {conciergeExists && <button type="submit" name="service" value="concierge">Remove Concierge API service</button>}
            {conciergeWebExists && <button type="submit" name="service" value="concierge_web">Remove Concierge Web UI service</button>}
            {ollamaExists && <button type="submit" name="service" value="ollama">Remove Ollama service</button>}
            {keycloakExists && <button type="submit" name="service" value="keycloak">Remove Keycloak service</button>}
            {opensearchExists && <button type="submit" name="service" value="opensearch">Remove OpenSearch service</button>}
        </form>

    </section>)
}