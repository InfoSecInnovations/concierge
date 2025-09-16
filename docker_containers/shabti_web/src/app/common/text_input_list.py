from htmltools import HTMLDependency
from shiny import ui, module

input_list_dep = HTMLDependency(
    "text_input_list",
    "0.1",
    source={"subdir": "docker_containers/shabti_web/src/app/text_input_list"},
    script={"src": "textListComponent.js", "type": "module"},
    all_files=True,
)


def output_list(id):
    return ui.div(
        input_list_dep,
        # Use resolve_id so that our component will work in a module
        id=module.resolve_id(id),
        class_="shiny-text-list-output",
    )
