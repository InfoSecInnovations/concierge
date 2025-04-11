from shiny import module, reactive, ui, Inputs, Outputs, Session
from .doc_link import doc_link
from .markdown_renderer import md
from concierge_types import DocumentInfo
from typing import Callable, Coroutine, Any

# --------
# DOCUMENT
# --------


@module.ui
def document_ui(collection_name, doc, can_delete):
    card_elements = [
        ui.markdown(
            f"""
{doc_link(collection_name, doc)}

{doc["vector_count"]} vectors
""",
            render_func=md.render,
        )
    ]
    if can_delete:
        card_elements.append(ui.input_task_button("delete_doc", "Delete"))
    return ui.card(*card_elements)


@module.server
def document_server(
    input: Inputs,
    output: Outputs,
    session: Session,
    delete_function: Coroutine[Any, Any, str],
    collection,
    doc: DocumentInfo,
    deletion_callback: Callable[[], None],
):
    deleting = reactive.value(False)

    @ui.bind_task_button(button_id="delete_doc")
    @reactive.extended_task
    async def delete():
        return await delete_function(
                collection,
                doc.type,
                doc.document_id,
            )

    @reactive.effect()
    def delete_effect():
        delete.result()
        deleting.set(False)

    @reactive.effect
    @reactive.event(input.delete_doc, ignore_init=True)
    def on_delete():
        deleting.set(True)
        delete()

    @reactive.effect
    @reactive.event(deleting, ignore_none=False, ignore_init=True)
    def on_delete_done():
        if not deleting.get():
            deletion_callback()