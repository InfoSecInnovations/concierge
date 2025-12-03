from shiny import module, reactive, render, ui, Inputs, Outputs, Session
from .collection_document import document_ui, document_server


@module.ui
def document_list_ui():
    return [ui.output_ui("search_view"), ui.output_ui("document_list_view")]


@module.server
def document_list_server(
    input: Inputs,
    output: Outputs,
    session: Session,
    selected_collection,
    current_docs,
    delete_function,
    on_delete_document,
):
    @render.ui
    def document_list_view():
        return [
            document_ui(doc.element_id, selected_collection.get(), doc, True)
            for doc in current_docs.get()
        ]

    @render.ui
    def search_view():
        return ui.markdown("TODO")

    @reactive.effect
    def document_servers():
        for doc in current_docs.get():
            document_server(
                doc.element_id,
                delete_function,
                selected_collection.get(),
                doc,
                on_delete_document,
            )
