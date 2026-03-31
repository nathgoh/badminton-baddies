from __future__ import annotations

from queue import SimpleQueue
from threading import Lock

from schemas import FrameEvent


class AnalysisFeedManager:
    """Manages per-analysis event queues for SSE consumers.

    Thread-safe: producers call push() from worker threads,
    consumers read from the returned Queue.
    """

    def __init__(self) -> None:
        self._queues: dict[str, list[SimpleQueue[FrameEvent | None]]] = {}
        self._latest_events: dict[str, FrameEvent] = {}
        self._completed: set[str] = set()
        self._lock = Lock()

    def subscribe(self, analysis_id: str) -> SimpleQueue[FrameEvent | None]:
        queue: SimpleQueue[FrameEvent | None] = SimpleQueue()
        with self._lock:
            latest_event = self._latest_events.get(analysis_id)
            is_completed = analysis_id in self._completed
            if not is_completed:
                self._queues.setdefault(analysis_id, []).append(queue)
        if latest_event is not None:
            queue.put(latest_event)
        if is_completed:
            queue.put(None)
        return queue

    def unsubscribe(self, analysis_id: str, queue: SimpleQueue[FrameEvent | None]) -> None:
        with self._lock:
            queues = self._queues.get(analysis_id, [])
            try:
                queues.remove(queue)
            except ValueError:
                pass
            if not queues:
                self._queues.pop(analysis_id, None)

    def push(self, analysis_id: str, event: FrameEvent) -> None:
        with self._lock:
            self._latest_events[analysis_id] = event
            queues = list(self._queues.get(analysis_id, []))
        for queue in queues:
            queue.put(event)

    def complete(self, analysis_id: str) -> None:
        with self._lock:
            self._completed.add(analysis_id)
            queues = self._queues.pop(analysis_id, [])
        for queue in queues:
            queue.put(None)

    def reset(self, analysis_id: str) -> None:
        with self._lock:
            self._queues.pop(analysis_id, None)
            self._latest_events.pop(analysis_id, None)
            self._completed.discard(analysis_id)

    def discard(self, analysis_id: str) -> None:
        self.reset(analysis_id)
