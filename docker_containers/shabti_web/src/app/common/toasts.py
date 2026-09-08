"""Where every toast this app raises goes, and how the bars inside one are driven.

A progress toast is shown once and then patched in place by `progress_toast.js`, rather than being
re-rendered. That is what makes one mechanism work for both callers: `load_models` runs inside a
`@reactive.extended_task`, where setting a `reactive.Value` invalidates but never flushes, so an
output inside the toast would not update until the browser happened to send an unrelated message
(py-shiny #1785). Writing straight to the socket is what `ui.Progress` does internally, and it works
from anywhere.

Shared in its own module so that `ingest_job` can raise a toast without importing `ingester`, which
imports it.
"""

from shiny import ui
from shiny.session import require_active_session
from dataclasses import dataclass
import asyncio

# bslib's toast container, which is the only progress surface this app has. nothing renders into
# Shiny's own notification panel any more
TOAST_POSITION = "bottom-right"
# one handler for the whole app: `send_custom_message` does not namespace its type the way
# `send_input_message` namespaces its id, so the toast id has to travel in the payload
PROGRESS_MESSAGE = "shabtiProgress"


def show_message(message: str, type: str | None = None, duration_s: int | None = 5):
    """A toast that says one thing and goes away."""
    ui.show_toast(
        ui.toast(message, type=type, duration_s=duration_s, position=TOAST_POSITION)
    )


@dataclass
class ProgressRow:
    """One bar, and the two lines of text around it."""

    key: str
    label: str = ""
    detail: str = ""
    # None renders an indeterminate striped bar: work that is known to be happening but has not
    # reported a number yet
    percent: int | None = None
    # "success" or "danger", to colour a finished row by how it finished
    variant: str | None = None


def progress_body(status: str = ""):
    return ui.div(
        ui.div(status, class_="small text-muted", **{"data-progress-status": ""}),
        # filled in client side, because how many rows there are changes as work starts and
        # finishes, and re-showing the toast to re-render them would replace the element and
        # rebind everything inside it
        ui.div(**{"data-progress-rows": ""}),
    )


class ProgressToast:
    """A toast with one bar per thing currently in progress.

    Shown once and never re-shown: showing a toast on an id that is already up removes the element
    and inserts a new one, which would rebind any button inside it at zero and report that zero.
    Everything that moves is patched instead.
    """

    def __init__(
        self,
        toast_id: str,
        header: str,
        *extra,
        closable: bool = True,
        hide_when_empty: bool = False,
    ):
        self.toast_id = toast_id
        self._header = header
        self._extra = extra
        self._closable = closable
        # for a toast whose rows are independent loaders rather than one poll's worth of work:
        # the last one to finish takes the toast down with it
        self._hide_when_empty = hide_when_empty
        self._rows: dict[str, ProgressRow] = {}
        self._status = ""
        self._shown = False

    async def show(self):
        if self._shown:
            return
        self._shown = True
        ui.show_toast(
            ui.toast(
                progress_body(self._status),
                *self._extra,
                header=self._header,
                id=self.toast_id,
                duration_s=None,
                closable=self._closable,
                position=TOAST_POSITION,
                # so CSS can order these above toasts that don't auto-hide: this one holds the
                # Cancel button, and has to stay where the container scrolls to by default
                class_="shabti-progress",
            )
        )
        # `show_toast` sends synchronously, which can leave a partly run coroutine behind; py-shiny
        # yields for the same reason after its own progress sends (posit-dev/py-shiny#1381)
        await asyncio.sleep(0)

    def hide(self):
        ui.hide_toast(self.toast_id)
        self._shown = False
        self._rows.clear()

    async def set_rows(self, rows: list[ProgressRow], status: str | None = None):
        """Replace every row at once, for a caller that recomputes the lot each time."""
        self._rows = {row.key: row for row in rows}
        await self._send(status)

    async def set_row(self, row: ProgressRow, status: str | None = None):
        """Add or update one row, for a caller that only knows about its own work."""
        self._rows[row.key] = row
        await self._send(status)

    async def set_status(self, status: str):
        """Change the line above the bars without touching them."""
        await self._send(status)

    async def drop_row(self, key: str):
        self._rows.pop(key, None)
        if self._hide_when_empty and not self._rows:
            self.hide()
            return
        await self._send()

    async def _send(self, status: str | None = None):
        if status is not None:
            self._status = status
        await self.show()
        session = require_active_session(None)
        await session.send_custom_message(
            PROGRESS_MESSAGE,
            {
                "id": self.toast_id,
                "status": self._status,
                "rows": [
                    {
                        "key": row.key,
                        "label": row.label,
                        "detail": row.detail,
                        "percent": row.percent,
                        "variant": row.variant,
                    }
                    for row in self._rows.values()
                ],
            },
        )
