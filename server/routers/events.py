from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from ..watcher import subscribe, unsubscribe

router = APIRouter(prefix="/api")

_KEEPALIVE_SECONDS = 15


@router.get("/events")
async def events(request: Request) -> StreamingResponse:
    q = subscribe()

    async def generate():
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    event = await asyncio.wait_for(q.get(), timeout=_KEEPALIVE_SECONDS)
                    yield f"data: {json.dumps(event)}\n\n"
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
        finally:
            unsubscribe(q)

    return StreamingResponse(generate(), media_type="text/event-stream")
