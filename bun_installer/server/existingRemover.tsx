import { dockerItemExists } from "./dockerItemsExist"

export const ExistingRemover = async () => {
    const [conciergeExists, ollamaExists, keycloakExists, opensearchExists] = await Promise.all([
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
        ]).then(res => res.some(exists => exists))
    ])
    if (!conciergeExists && !ollamaExists && !keycloakExists && !opensearchExists) return <></>
    return (<>
        <h3>Remove existing Docker services (containers and related volumes)</h3>
        <p>This can help you if your installation appears to be broken or you want to create a fresh install.</p>
        <p>If you're switching between having security enabled and disabled or vice-versa, it's strongly recommended that you remove all existing containers except for Ollama.</p>
        <p>Be aware that if you remove Ollama you will have to redownload the LLM models which are quite large.</p>
        {conciergeExists && <>
            <form action="/remove_concierge" method="post">
                <button type="submit">Remove Concierge service</button>
            </form>           
        </>}
        {ollamaExists && <>
            <form action="/remove_ollama" method="post">
                <button type="submit">Remove Ollama service</button>
            </form>           
        </>}
        {keycloakExists && <>
            <form action="/remove_keycloak" method="post">
                <button type="submit">Remove Keycloak service</button>
            </form>           
        </>}
        {opensearchExists && <>
            <form action="/remove_opensearch" method="post">
                <button type="submit">Remove OpenSearch service</button>
            </form>           
        </>}
    </>)
}