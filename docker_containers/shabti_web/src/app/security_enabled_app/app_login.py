from shiny import App, ui, Inputs, Outputs, Session, reactive, render
from shabti_keycloak import get_keycloak_client

scope = "profile email openid offline_access"

app_ui = ui.page_fillable(
    ui.output_ui("script_output"),
    ui.markdown("# Shabti AI"),
    ui.div(ui.input_action_button("login_button", "Log In")),
    gap="1em",
)


def server(input: Inputs, output: Outputs, session: Session):
    @reactive.effect
    @reactive.event(input.login_button, ignore_init=True)
    def on_click():
        @render.ui
        def script_output():
            redirect_uri = f"{session.http_conn.headers['origin']}/callback"
            keycloak_openid = get_keycloak_client()
            authorization_url = keycloak_openid.auth_url(
                redirect_uri=redirect_uri, scope=scope
            )
            return ui.tags.script(f'window.location.href = "{authorization_url}"')


app = App(app_ui, server)
