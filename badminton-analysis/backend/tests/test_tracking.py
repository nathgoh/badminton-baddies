from services.tracking import compute_iou, track_person_in_frame
from models.schemas import BoundingBox


def test_iou_identical_boxes():
    box = BoundingBox(id=0, x=0, y=0, width=100, height=100, confidence=0.9)
    assert compute_iou(box, box) == 1.0


def test_iou_no_overlap():
    box_a = BoundingBox(id=0, x=0, y=0, width=50, height=50, confidence=0.9)
    box_b = BoundingBox(id=1, x=100, y=100, width=50, height=50, confidence=0.9)
    assert compute_iou(box_a, box_b) == 0.0


def test_iou_partial_overlap():
    box_a = BoundingBox(id=0, x=0, y=0, width=100, height=100, confidence=0.9)
    box_b = BoundingBox(id=1, x=50, y=50, width=100, height=100, confidence=0.9)
    iou = compute_iou(box_a, box_b)
    assert 0.1 < iou < 0.3  # ~14.3% overlap


def test_track_person_match():
    prev_box = BoundingBox(id=0, x=10, y=10, width=50, height=100, confidence=0.9)
    candidates = [
        BoundingBox(id=0, x=200, y=200, width=50, height=100, confidence=0.8),
        BoundingBox(id=1, x=12, y=11, width=50, height=100, confidence=0.85),
    ]
    matched = track_person_in_frame(prev_box, candidates)
    assert matched is not None
    assert matched.x == 12


def test_track_person_no_match():
    prev_box = BoundingBox(id=0, x=10, y=10, width=50, height=100, confidence=0.9)
    candidates = [
        BoundingBox(id=0, x=500, y=500, width=50, height=100, confidence=0.8),
    ]
    matched = track_person_in_frame(prev_box, candidates, iou_threshold=0.3)
    assert matched is None
