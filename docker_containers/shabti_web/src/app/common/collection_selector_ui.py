from shiny import module, ui


@module.ui
def collection_selector_ui():
    return [ui.output_ui("collection_selector")]
