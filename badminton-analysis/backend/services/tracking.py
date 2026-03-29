from models.schemas import BoundingBox


def compute_iou(box_a: BoundingBox, box_b: BoundingBox) -> float:
    x_left = max(box_a.x, box_b.x)
    y_top = max(box_a.y, box_b.y)
    x_right = min(box_a.x + box_a.width, box_b.x + box_b.width)
    y_bottom = min(box_a.y + box_a.height, box_b.y + box_b.height)

    if x_right <= x_left or y_bottom <= y_top:
        return 0.0

    intersection = (x_right - x_left) * (y_bottom - y_top)
    area_a = box_a.width * box_a.height
    area_b = box_b.width * box_b.height
    union = area_a + area_b - intersection

    if union == 0:
        return 0.0

    return intersection / union


def track_person_in_frame(
    prev_box: BoundingBox,
    candidates: list[BoundingBox],
    iou_threshold: float = 0.2,
) -> BoundingBox | None:
    best_match = None
    best_iou = 0.0

    for candidate in candidates:
        iou = compute_iou(prev_box, candidate)
        if iou > best_iou:
            best_iou = iou
            best_match = candidate

    if best_iou < iou_threshold:
        return None

    return best_match
