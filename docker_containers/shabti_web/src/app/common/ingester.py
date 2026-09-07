from shiny import ui, reactive, render, Inputs, Outputs, Session, module
from .text_input_list import text_input_list
from dataclasses import dataclass, field
from shabti_types import IngestInfo
from shabti_api_client import BaseShabtiClient, ShabtiRequestError
from .collections_data import CollectionsData
from .ingest_job import cancel_button_server, ingest_job_card, is_active
from .load_models import load_models
import os
import time

# the API's own listing route anticipates being polled about this often while something is running
POLL_ACTIVE_SECONDS = 1
# idle, this is only watching for a job started from another tab or the CLI, at the rate status.py
# already polls at
POLL_IDLE_SECONDS = 10
# the API keeps a finished ingest for an hour, which is far more history than this panel wants:
# long enough that a reload right after a job ended still shows how it went, and no longer
FINISHED_VISIBLE_SECONDS = 300


@dataclass
class Submission:
    """One POST waiting to be sent.

    The inputs don't block any more, so submissions can arrive faster than the uploads leave. They
    can't all be in flight at once: re-invoking an extended task cancels the call it is already
    making, and for an upload that means losing the file.
    """

    collection_id: str
    files: list[str] = field(default_factory=list)
    urls: list[str] = field(default_factory=list)


def is_visible(job: IngestInfo) -> bool:
    if is_active(job):
        return True
    return (job.finished or 0) > (time.time() - FINISHED_VISIBLE_SECONDS) * 1000


def submit_error_text(error: Exception) -> str:
    if not isinstance(error, ShabtiRequestError):
        return str(error)
    if error.status_code == 403:
        # the wording the collection view already uses for the same denial
        return "You don't have permission to ingest documents into this collection"
    body = error.message["message"]
    return body.get("message") if isinstance(body, dict) else str(body)


@module.ui
def ingester_ui():
    return ui.accordion_panel(
        ui.markdown("#### Ingest Documents"),
        ui.output_ui("ingester_content"),
        value="ingest_documents",
    )


@module.ui
def ingest_jobs_ui():
    # deliberately given the same module id as `ingester_server`: jobs span collections, so this
    # panel is shown even where the selected collection can't be ingested into
    return ui.accordion_panel(
        ui.output_ui("ingest_jobs_title"),
        ui.output_ui("ingest_jobs_content"),
        value="ingest_jobs",
    )


@module.server
def ingester_server(
    input: Inputs,
    output: Outputs,
    session: Session,
    client: BaseShabtiClient,
    selected_collection: reactive.Value,
    collections: reactive.Value[CollectionsData],
    llm_status: reactive.Value,
):
    file_input_trigger = reactive.value(0)
    url_input_trigger = reactive.value(0)
    ingesting_done = reactive.value(0)
    ingest_started = reactive.value(0)
    embedding_model_loaded = reactive.value(False)
    jobs: reactive.Value[list[IngestInfo]] = reactive.value([])
    cancelling: reactive.Value[set[str]] = reactive.value(set())
    submit_queue: reactive.Value[list[Submission]] = reactive.value([])
    # bookkeeping nothing renders from, so plain sets rather than reactive values
    seen_terminal: set[str] = set()
    started_servers: set[str] = set()
    polled_once = reactive.value(False)
    # tracked here rather than read off the tasks, because one call at a time is a correctness
    # requirement for both of them: re-invoking an extended task cancels the call it is already
    # making, and for an upload that means losing the file
    polling = reactive.value(False)
    submitting = reactive.value(False)

    @render.ui
    def ingester_content():
        if not llm_status.get():
            return ui.markdown("Waiting for LLM host to come online...")
        if not embedding_model_loaded.get():
            return ui.markdown("Loading embeddings model...")
        return ui.TagList(
            ui.markdown("#### Files"),
            ui.output_ui("file_input"),
            ui.markdown("#### URLs"),
            ui.output_ui("url_input"),
            # not a task button: with nothing to bind it to it would enter its busy state on click
            # and never leave it. the jobs panel is the feedback now
            ui.input_action_button(id="ingest", label="Ingest"),
        )

    @render.ui
    @reactive.event(file_input_trigger, ignore_none=False, ignore_init=False)
    def file_input():
        return ui.input_file(id="ingester_files", label=None, multiple=True)

    @render.ui
    @reactive.event(url_input_trigger, ignore_none=False, ignore_init=False)
    def url_input():
        return text_input_list("url_input_list")

    @reactive.extended_task
    async def fetch_ingests() -> list[IngestInfo] | None:
        try:
            return await client.get_ingests()
        except Exception:
            # anything at all, because this is what clears `polling`: a listing that raised out of
            # here would stop the poll for the rest of the session. the API going away is ordinary
            # during a restart, and the status widget already says so
            return None

    def poll_now():
        # a tick landing while the API is still answering is skipped rather than taken, or a slow
        # listing would be cancelled and retried forever and never return anything
        with reactive.isolate():
            if polling.get():
                return
            polling.set(True)
        fetch_ingests()

    @reactive.effect
    def poll_ingests():
        # isolated so the effect's only dependency is its own timer: reading `jobs` reactively would
        # re-run it on every result and stack a timer per poll
        with reactive.isolate():
            interval = (
                POLL_ACTIVE_SECONDS
                if any(is_active(job) for job in jobs.get())
                else POLL_IDLE_SECONDS
            )
        poll_now()
        reactive.invalidate_later(interval)

    @reactive.effect
    def ingests_effect():
        latest = fetch_ingests.result()
        with reactive.isolate():
            polling.set(False)
        if latest is None:
            return
        with reactive.isolate():
            first_poll = not polled_once.get()
            for job in latest:
                if is_active(job) or job.ingest_id in seen_terminal:
                    continue
                seen_terminal.add(job.ingest_id)
                # the first poll of a session sees up to an hour of finished jobs. refreshing for
                # those would force the documents panel open on every single page load
                if not first_poll and job.collection_id == selected_collection.get():
                    ingesting_done.set(ingesting_done.get() + 1)
            polled_once.set(True)
            visible = sorted(
                (job for job in latest if is_visible(job)),
                key=lambda job: job.started,
                reverse=True,
            )
            # the panel is rendered wholesale, so don't churn the DOM when nothing has moved
            if visible != jobs.get():
                jobs.set(visible)

    @reactive.extended_task
    async def start_ingests(submissions: list[Submission]) -> list[str]:
        errors = []
        for submission in submissions:
            try:
                if submission.files:
                    await client.start_files_ingest(
                        submission.collection_id, submission.files
                    )
                else:
                    await client.start_urls_ingest(
                        submission.collection_id, submission.urls
                    )
            except Exception as e:
                # per submission, and anything at all: one failure must not take the rest of the
                # queue with it, nor leave `submitting` stuck and block every later one. a denial
                # arrives here now rather than on the first line of the stream this used to return
                errors.append(submit_error_text(e))
        return errors

    @reactive.effect
    def drain_submit_queue():
        # woken by a new submission and again when the POST before it finishes
        if submitting.get():
            return
        queued = submit_queue.get()
        if not queued:
            return
        with reactive.isolate():
            submit_queue.set([])
            submitting.set(True)
        start_ingests(queued)

    @reactive.effect
    def start_ingests_effect():
        errors = start_ingests.result()
        with reactive.isolate():
            submitting.set(False)
        for message in errors:
            ui.notification_show(message, type="error")
        # rather than waiting out the poll interval to show what was just submitted
        poll_now()

    @reactive.effect
    @reactive.event(input.ingester_files, ignore_none=True, ignore_init=True)
    def handle_file_upload():
        files = input.ingester_files()
        if not len(files):
            return
        # we want to conserve the original file names
        named_files = []
        for file in files:
            named_file = os.path.join(os.path.dirname(file["datapath"]), file["name"])
            os.rename(file["datapath"], named_file)
            named_files.append(named_file)
        collection_id = selected_collection.get()
        print(f"ingesting documents into collection {collection_id}")
        # the input keeps whatever was chosen, so it is replaced to let the same file be picked
        # twice. blanking it out during the ingest used to do this
        file_input_trigger.set(file_input_trigger.get() + 1)
        submit_queue.set(
            [*submit_queue.get(), Submission(collection_id, files=named_files)]
        )
        ingest_started.set(ingest_started.get() + 1)

    @reactive.effect
    @reactive.event(input.ingest, ignore_none=False, ignore_init=True)
    def handle_url_ingest_click():
        urls = input.url_input_list()
        if not urls or not len(urls):
            return
        collection_id = selected_collection.get()
        print(f"ingesting documents into collection {collection_id}")
        # replaced to clear the submitted URLs, which blanking the list out used to do
        url_input_trigger.set(url_input_trigger.get() + 1)
        submit_queue.set([*submit_queue.get(), Submission(collection_id, urls=urls)])
        ingest_started.set(ingest_started.get() + 1)

    @render.ui
    def ingest_jobs_title():
        active = len([job for job in jobs.get() if is_active(job)])
        return ui.markdown(f"#### Ingest Jobs{f' ({active} active)' if active else ''}")

    @render.ui
    def ingest_jobs_content():
        current = jobs.get()
        if not current:
            return ui.markdown("No recent ingest jobs")
        known = collections.get().collections
        return [
            ingest_job_card(
                job,
                # jobs span collections, so say which one when it isn't the one on screen
                known[job.collection_id].collection_name
                if job.collection_id != selected_collection.get()
                and job.collection_id in known
                else None,
                job.ingest_id in cancelling.get(),
            )
            for job in current
        ]

    @reactive.effect
    def cancel_button_servers():
        for job in jobs.get():
            # unlike document_list's rand_hex element ids, an ingest id is stable across polls, so
            # creating a server per pass would stack up an observer a second
            if job.ingest_id in started_servers:
                continue
            started_servers.add(job.ingest_id)
            cancel_button_server(job.ingest_id, client, job.ingest_id, cancelling)

    @reactive.extended_task
    async def load_embedding_model():
        models = await client.get_models()
        embeddings = next(m for m in models["data"] if "embeddings" in m["tags"])
        await load_models(client, embeddings["id"])

    @reactive.effect
    def load_model_effect():
        load_embedding_model.result()
        embedding_model_loaded.set(True)

    @reactive.effect
    def init():
        if llm_status.get() and not embedding_model_loaded.get():
            load_embedding_model()

    # the accordion this lives in belongs to the parent, so opening the jobs panel on a submission
    # is its call to make, the same way finishing one already reveals the documents panel
    return ingesting_done, ingest_started
