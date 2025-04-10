from shiny import reactive

def update_status_reactives(status: reactive.Calc_[dict[str, bool]], opensearch_status: reactive.Value, ollama_status: reactive.Value):
    current_status = status()
    opensearch_status.set(current_status["opensearch"])
    ollama_status.set(current_status["ollama"])