from shiny import reactive


def update_status_reactives(
    status: reactive.Calc_[dict[str, bool]],
    api_status: reactive.Value,
    opensearch_status: reactive.Value,
    ollama_status: reactive.Value,
):
    current_status = status()
    api_status.set(current_status["api"])
    opensearch_status.set(current_status["opensearch"])
    ollama_status.set(current_status["ollama"])
