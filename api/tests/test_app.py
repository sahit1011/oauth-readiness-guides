import asyncio
import os
import time
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

os.environ.setdefault("WEB_ORIGIN", "http://localhost:3000")  # read when the module is imported
from oauth_guides_api import app as api  # noqa: E402


class SlowStore:
    """Every visitor is under the daily limit, but each claim takes long enough for requests to overlap."""

    def find(self, query):
        return None

    def claim_generation(self, ip, limit, window_seconds):
        time.sleep(0.2)
        return True


def test_concurrent_starts_never_exceed_the_running_job_cap(monkeypatch):
    release = asyncio.Event()

    async def held_run(job, query):
        await release.wait()

    monkeypatch.setattr(api, "_run", held_run)
    monkeypatch.setattr(api, "_jobs", {})
    monkeypatch.setattr(api.app.state, "store", SlowStore(), raising=False)

    async def start(i: int):
        http = SimpleNamespace(headers={"true-client-ip": f"visitor-{i}"}, client=SimpleNamespace(host="127.0.0.1"))
        try:
            return await api.start_generation(api.GenerateRequest(query=f"app {i}", regenerate=True), http)
        except HTTPException as exc:
            return exc.status_code

    async def scenario():
        results = await asyncio.gather(*(start(i) for i in range(6)))
        release.set()
        return results

    results = asyncio.run(scenario())
    assert sum(isinstance(r, dict) for r in results) == api.MAX_CONCURRENT_JOBS
    assert results.count(429) == 6 - api.MAX_CONCURRENT_JOBS
