from __future__ import annotations

from queue import SimpleQueue

from schemas import FrameEvent


class AnalysisFeedManager:
    """Manages per-analysis event queues for SSE consumers.

    Thread-safe: producers call push() from worker threads,
    consumers read from the returned Queue.
    """

    def __init__(self) -> None:
        self._queues: dict[str, list[SimpleQueue[FrameEvent | None]]] = {}

    def subscribe(self, analysis_id: str) -> SimpleQueue[FrameEvent | None]:
        queue: SimpleQueue[FrameEvent | None] = SimpleQueue()
        self._queues.setdefault(analysis_id, []).append(queue)
        return queue

    def unsubscribe(self, analysis_id: str, queue: SimpleQueue[FrameEvent | None]) -> None:
        queues = self._queues.get(analysis_id, [])
        try:
            queues.remove(queue)
        except ValueError:
            pass
        if not queues:
            self._queues.pop(analysis_id, None)

    def push(self, analysis_id: str, event: FrameEvent) -> None:
        for queue in self._queues.get(analysis_id, []):
            queue.put(event)

    def complete(self, analysis_id: str) -> None:
        for queue in self._queues.get(analysis_id, []):
            queue.put(None)
        self._queues.pop(analysis_id, None)
