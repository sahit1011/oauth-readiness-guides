"""HTTP API: the guide library, and live generation jobs streamed over server-sent events."""

import asyncio
import json
import logging
import time
import uuid
from collections import defaultdict
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sse_starlette import EventSourceResponse

from .agent import make_composio
from .llm import LLM, require_env
from .pipeline import generate
from .store import Store, StoredGuide

log = logging.getLogger(__name__)

_TERMINAL = ("done", "error")
# Chosen, not sourced: each run spends LLM credit and holds a worker thread for minutes.
MAX_CONCURRENT_JOBS = 3
# Chosen, not sourced: lets a reviewer try several apps without a public link running up a bill.
JOBS_PER_IP_PER_HOUR = 5
_HOUR_SECONDS = 3600
# Single API instance assumed (see Job); limits reset on restart.
_starts_by_ip: dict[str, list[float]] = defaultdict(list)


@dataclass
class Job:
    """In-process job state. Single API instance assumed: jobs do not survive a restart."""

    events: list[dict] = field(default_factory=list)
    changed: asyncio.Condition = field(default_factory=asyncio.Condition)
    task: asyncio.Task | None = None


_jobs: dict[str, Job] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.store = Store(require_env("GUIDES_DATABASE_URL"))
    app.state.llm = LLM()
    app.state.composio = make_composio()
    yield


app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware, allow_origins=[require_env("WEB_ORIGIN")], allow_methods=["GET", "POST"], allow_headers=["content-type"]
)


class GenerateRequest(BaseModel):
    query: str = Field(min_length=2, max_length=200, description="App name or website")
    regenerate: bool = Field(False, description="Generate even when the library already has a guide for this app")


async def _publish(job: Job, event: dict) -> None:
    async with job.changed:
        job.events.append(event)
        job.changed.notify_all()


async def _run(job: Job, query: str) -> None:
    loop = asyncio.get_running_loop()

    def emit(event: dict) -> None:
        asyncio.run_coroutine_threadsafe(_publish(job, event), loop).result()

    try:
        await asyncio.to_thread(
            generate, query, llm=app.state.llm, composio=app.state.composio, store=app.state.store, emit=emit
        )
    # Job boundary: the failure is reported to the watching client and logged with its traceback.
    except Exception as exc:
        log.exception("generation failed for %r", query)
        await _publish(job, {"type": "error", "message": f"{type(exc).__name__}: {exc}"})


@app.post("/api/generate")
async def start_generation(request: GenerateRequest, http: Request) -> dict:
    if not request.regenerate:
        existing = await asyncio.to_thread(app.state.store.find, request.query)
        if existing is not None:
            return {"existing": {"slug": existing.guide.slug, "app_name": existing.guide.draft.app_name, "curated": existing.curated}}

    if sum(1 for j in _jobs.values() if j.task is not None and not j.task.done()) >= MAX_CONCURRENT_JOBS:
        raise HTTPException(429, f"{MAX_CONCURRENT_JOBS} guides are already being generated; try again in a few minutes")
    # Behind Railway's proxy this is the client IP only when uvicorn runs with --proxy-headers.
    ip = http.client.host
    now = time.monotonic()
    recent = [t for t in _starts_by_ip[ip] if now - t < _HOUR_SECONDS]
    if len(recent) >= JOBS_PER_IP_PER_HOUR:
        raise HTTPException(429, f"limit of {JOBS_PER_IP_PER_HOUR} generations per hour reached; try again later")
    _starts_by_ip[ip] = [*recent, now]

    job_id = uuid.uuid4().hex
    job = Job()
    _jobs[job_id] = job
    job.task = asyncio.create_task(_run(job, request.query))
    return {"job_id": job_id}


@app.get("/api/jobs/{job_id}/events")
async def job_events(job_id: str) -> EventSourceResponse:
    if job_id not in _jobs:
        raise HTTPException(404, f"no job {job_id}")
    job = _jobs[job_id]

    async def stream() -> AsyncIterator[dict]:
        sent = 0
        while True:
            async with job.changed:
                await job.changed.wait_for(lambda: len(job.events) > sent)
                pending = job.events[sent:]
            for event in pending:
                sent += 1
                yield {"event": event["type"], "data": json.dumps(event)}
                if event["type"] in _TERMINAL:
                    return

    return EventSourceResponse(stream())


@app.get("/api/guides")
def list_guides() -> list[dict]:
    return [
        {
            "slug": s.guide.slug,
            "version": s.version,
            "curated": s.curated,
            "app_name": s.guide.draft.app_name,
            "website": s.guide.draft.website,
            "summary": s.guide.draft.summary,
            "tier": s.guide.tier.model_dump(),
            "totals": s.guide.totals.model_dump(),
            "generated_at": s.guide.provenance.generated_at.isoformat(),
        }
        for s in app.state.store.list_preferred()
    ]


@app.get("/api/guides/{slug}")
def get_guide(slug: str, v: int | None = None) -> StoredGuide:
    """The preferred version (latest curated, else latest), or version `v` when given."""
    stored = app.state.store.get(slug, v)
    if stored is None:
        raise HTTPException(404, f"no guide for {slug}" + ("" if v is None else f" version {v}"))
    return stored
