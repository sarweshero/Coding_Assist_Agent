import asyncio
from typing import AsyncGenerator, Dict

from fastapi.responses import StreamingResponse


class SSEManager:
    def __init__(self) -> None:
        self._queues: Dict[str, asyncio.Queue] = {}

    def create_stream(self, project_id: str) -> AsyncGenerator[str, None]:
        queue: asyncio.Queue = self._queues.setdefault(project_id, asyncio.Queue(maxsize=200))

        async def event_stream():
            try:
                while True:
                    event = await queue.get()
                    yield f"data: {event}\n\n"
            finally:
                self._queues.pop(project_id, None)

        return event_stream()

    def emit(self, channel: str, event: dict) -> None:
        queue = self._queues.get(channel)
        if queue is None:
            return
        try:
            queue.put_nowait(str(event))
        except asyncio.QueueFull:
            pass


sse_manager = SSEManager()
