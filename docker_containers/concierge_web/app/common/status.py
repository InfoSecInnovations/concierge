from shiny import module, reactive, ui, render, Inputs, Outputs, Session, req
from concierge_api_client import BaseConciergeClient


@module.ui
def status_ui():
    return ui.output_ui("status_widget")


@module.server
def status_server(
    input: Inputs, output: Outputs, session: Session, client: BaseConciergeClient
):
    opensearch_status = reactive.value("loading")
    ollama_status = reactive.value("loading")

    @reactive.extended_task
    async def get_ollama_status():
        return await client.ollama_status()

    @reactive.extended_task
    async def get_opensearch_status():
        return await client.opensearch_status()

    @reactive.effect
    def set_ollama_status():
        ollama_status.set("online" if get_ollama_status.result() else "offline")

    @reactive.effect
    def set_opensearch_status():
        opensearch_status.set("online" if get_opensearch_status.result() else "offline")

    @reactive.effect
    def poll():
        reactive.invalidate_later(10)
        get_ollama_status()
        get_opensearch_status()

    @render.ui
    def status_widget():
        items = []
        if opensearch_status.get() != "loading":
            items.append(
                ui.markdown(
                    f"{'🟢' if opensearch_status.get() == 'online' else '🔴'} OpenSearch"
                )
            )
        if ollama_status.get() != "loading":
            items.append(
                ui.markdown(
                    f"{'🟢' if ollama_status.get() == 'online' else '🔴'} Ollama"
                )
            )
        req(items)
        return ui.card(*items)

    @reactive.calc
    def result():
        return {
            "opensearch": opensearch_status.get() == "online",
            "ollama": ollama_status.get() == "online",
        }

    return result
