from shiny import module, reactive, ui, render, Inputs, Outputs, Session, req
from shabti_api_client import BaseShabtiClient
from httpx import ConnectError


@module.ui
def status_ui():
    return ui.output_ui("status_widget")


@module.server
def status_server(
    input: Inputs, output: Outputs, session: Session, client: BaseShabtiClient
):
    opensearch_status = reactive.value("loading")
    ollama_status = reactive.value("loading")
    api_status = reactive.value("loading")

    @reactive.extended_task
    async def get_ollama_status():
        try:
            return "online" if await client.ollama_status() else "offline"
        except ConnectError:
            return "loading"

    @reactive.extended_task
    async def get_opensearch_status():
        try:
            return "online" if await client.opensearch_status() else "offline"
        except ConnectError:
            return "loading"

    @reactive.extended_task
    async def get_api_status():
        return "online" if await client.api_status() else "offline"

    @reactive.effect
    def set_ollama_status():
        ollama_status.set(get_ollama_status.result())

    @reactive.effect
    def set_opensearch_status():
        opensearch_status.set(get_opensearch_status.result())

    @reactive.effect
    def set_api_status():
        api_status.set(get_api_status.result())

    @reactive.effect
    def poll():
        reactive.invalidate_later(10)
        get_api_status()

    # the Ollama and OpenSearch statuses are obtained through the API, so the API needs to be online before we can verify the others
    @reactive.effect
    def on_api_status():
        reactive.invalidate_later(10)
        if api_status.get() == "online":
            get_ollama_status()
            get_opensearch_status()
        else:
            ollama_status.set("loading")
            opensearch_status.set("loading")

    @render.ui
    def status_widget():
        items = []
        if api_status.get() != "loading":
            items.append(
                ui.markdown(
                    f"{'🟢' if api_status.get() == 'online' else '🔴'} Shabti API Service"
                )
            )
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
            "api": api_status.get() == "online",
            "opensearch": opensearch_status.get() == "online",
            "ollama": ollama_status.get() == "online",
        }

    return result
