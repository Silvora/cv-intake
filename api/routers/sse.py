import asyncio

from fastapi import APIRouter, Query, Request
from fastapi.responses import StreamingResponse
from utils.sse_conn import conn

router = APIRouter(tags=["sse"])

@router.get("/sse")
async def stream_events(
    request: Request,
    stream_type: str = Query(default="results", alias="type"),
):
    normalized_type = stream_type.strip() or "results"
    queue = await conn.subscribe(normalized_type)

    async def event_stream():
        try:
            while True:
                if await request.is_disconnected():
                    break

                try:
                    message = await asyncio.wait_for(queue.get(), timeout=15)
                    yield message
                except asyncio.TimeoutError:
                    yield conn.heartbeat()
        finally:
            await conn.unsubscribe(normalized_type, queue)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
