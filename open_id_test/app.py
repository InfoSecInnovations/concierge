import urllib.parse
from shiny import App, ui, Inputs, Outputs, Session, render
import dotenv
import os
from requests_oauthlib import OAuth2Session

dotenv.load_dotenv()

client_id = os.getenv("OAUTH2_CLIENT_ID")
client_secret = os.getenv("OAUTH2_CLIENT_SECRET")
redirect_uri = "http://127.0.0.1:60721/"
scope = ["openid"]
authorization_endpoint = "https://accounts.google.com/o/oauth2/auth"
token_endpoint = "https://accounts.google.com/o/oauth2/token"

app_ui = ui.page_auto(ui.output_ui("openid_data"))


def server(input: Inputs, output: Outputs, session: Session):
    query_string = input[".clientdata_url_search"]._value
    if query_string:
        parsed = urllib.parse.parse_qs(query_string[1:])  # query string starts with ?

        if "code" in parsed:
            oauth = OAuth2Session(
                client_id, state=parsed["state"][0], redirect_uri=redirect_uri
            )
            print(parsed["code"][0])
            oauth.fetch_token(
                token_url=token_endpoint,
                client_secret=client_secret,
                code=parsed["code"][0],
            )
            r = oauth.get("https://www.googleapis.com/oauth2/v1/userinfo")

            @render.ui
            def openid_data():
                return ui.markdown(r.text)

            return

    oauth = OAuth2Session(client_id, redirect_uri=redirect_uri, scope=scope)
    authorization_url, state = oauth.authorization_url(
        authorization_endpoint,
        # access_type and prompt are Google specific extra
        # parameters.
        access_type="offline",
        prompt="select_account",
    )

    @render.ui
    def openid_data():
        return ui.markdown(f"<{authorization_url}>")


app = App(app_ui, server)
