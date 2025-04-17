from shiny import module, reactive, ui, render, Inputs, Outputs, Session
from concierge_api_client import BaseConciergeClient


@module.ui
def status_ui():
    return ui.output_ui("status_widget")


@module.server
def status_server(
    input: Inputs, output: Outputs, session: Session, client: BaseConciergeClient
):
    opensearch_status = reactive.value(False)
    ollama_status = reactive.value(False)

    @reactive.extended_task
    async def get_ollama_status():
        return await client.ollama_status()

    @reactive.extended_task
    async def get_opensearch_status():
        return await client.opensearch_status()

    @reactive.effect
    def set_ollama_status():
        ollama_status.set(get_ollama_status.result())

    @reactive.effect
    def set_opensearch_status():
        opensearch_status.set(get_opensearch_status.result())

    @reactive.effect
    def poll():
        reactive.invalidate_later(10)
        get_ollama_status()
        get_opensearch_status()

    @render.ui
    def status_widget():
        return ui.card(
            ui.markdown(f"{'🟢' if opensearch_status.get() else '🔴'} OpenSearch"),
            ui.markdown(f"{'🟢' if ollama_status.get() else '🔴'} Ollama"),
        )

    @reactive.calc
    def result():
        return {"opensearch": opensearch_status.get(), "ollama": ollama_status.get()}

    return result
