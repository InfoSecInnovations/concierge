# This shows a way to load permissions without breaking the picker

from shiny import App, ui, Inputs, Outputs, Session, reactive, render, req
import shinyswatch
import asyncio

app_ui = ui.page_auto(
    ui.output_ui("main_page"),
    theme=shinyswatch.theme.darkly,
)


def server(input: Inputs, output: Outputs, session: Session):
    shinyswatch.theme_picker_server()
    permissions = reactive.value(None)

    async def get_read():
        await asyncio.sleep(0.5)
        return True

    async def get_write():
        await asyncio.sleep(0.25)
        return True

    @reactive.extended_task
    async def collect_permissions():
        async with asyncio.TaskGroup() as tg:
            read_task = tg.create_task(get_read())
            write_task = tg.create_task(get_write())
        return {"read": read_task.result(), "write": write_task.result()}

    @reactive.effect
    def on_collect_permissions():
        permissions.set(collect_permissions.result())

    @render.ui
    def main_page():
        permissions_value = permissions.get()
        req(permissions_value)
        items = [ui.nav_panel("Home", ui.markdown("Home"))]
        if permissions_value["read"]:
            items.append(ui.nav_panel("Read", ui.markdown("Read")))
        if permissions_value["write"]:
            items.append(ui.nav_panel("Write", ui.markdown("Write")))
        return ui.navset_pill_list(
            *items, ui.nav_control(shinyswatch.theme_picker_ui())
        )

    @reactive.effect
    def update_access():
        collect_permissions()


app = App(app_ui, server)
