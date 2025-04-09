def update_status_reactives(status, opensearch_status, ollama_status):
    current_status = status()
    opensearch_status.set(current_status["opensearch"])
    ollama_status.set(current_status["ollama"])