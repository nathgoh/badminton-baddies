from analyses.feed import AnalysisFeedManager
from schemas import FrameEvent


def _make_event(analysis_id: str = "test-1", frame_index: int = 0) -> FrameEvent:
    return FrameEvent(
        analysis_id=analysis_id,
        pipeline_stage="tracking",
        frame_index=frame_index,
        total_frames=100,
        progress_percent=1,
        message="Tracking frame 0/100",
    )


def test_subscribe_and_push() -> None:
    manager = AnalysisFeedManager()
    queue = manager.subscribe("test-1")
    event = _make_event()
    manager.push("test-1", event)
    assert queue.get_nowait() == event


def test_push_without_subscribers_does_not_raise() -> None:
    manager = AnalysisFeedManager()
    manager.push("no-sub", _make_event(analysis_id="no-sub"))


def test_unsubscribe_removes_queue() -> None:
    manager = AnalysisFeedManager()
    queue = manager.subscribe("test-1")
    manager.unsubscribe("test-1", queue)
    manager.push("test-1", _make_event())


def test_complete_sends_sentinel() -> None:
    manager = AnalysisFeedManager()
    queue = manager.subscribe("test-1")
    manager.complete("test-1")
    assert queue.get_nowait() is None


def test_multiple_subscribers() -> None:
    manager = AnalysisFeedManager()
    q1 = manager.subscribe("test-1")
    q2 = manager.subscribe("test-1")
    event = _make_event()
    manager.push("test-1", event)
    assert q1.get_nowait() == event
    assert q2.get_nowait() == event
