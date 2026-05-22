import asyncio
import json
from collections import defaultdict
from typing import Any


def _format_sse(event: str, data: Any) -> str:
    payload = json.dumps(data, ensure_ascii=False)
    return f"event: {event}\ndata: {payload}\n\n"


class SSEConnectionManager:
    def __init__(self) -> None:
        self._subscribers: dict[str, set[asyncio.Queue[str]]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def subscribe(self, stream_type: str) -> asyncio.Queue[str]:
        queue: asyncio.Queue[str] = asyncio.Queue()
        async with self._lock:
            self._subscribers[stream_type].add(queue)
        return queue

    async def unsubscribe(self, stream_type: str, queue: asyncio.Queue[str]) -> None:
        async with self._lock:
            subscribers = self._subscribers.get(stream_type)
            if subscribers is None:
                return
            subscribers.discard(queue)
            if not subscribers:
                self._subscribers.pop(stream_type, None)

    async def publish(self, stream_type: str, data: Any) -> None:
        message = _format_sse(stream_type, data)
        async with self._lock:
            subscribers = list(self._subscribers.get(stream_type, set()))

        for queue in subscribers:
            queue.put_nowait(message)

    def heartbeat(self) -> str:
        return ": keepalive\n\n"


conn = SSEConnectionManager()
