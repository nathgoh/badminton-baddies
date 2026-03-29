from services.analysis import compute_stats

def test_compute_stats_basic():
    # Simulate 3 frames at 30fps with known positions
    frame_data = [
        {"time_sec": 0.0, "center_x": 100, "center_y": 200, "landmarks": None},
        {"time_sec": 0.033, "center_x": 110, "center_y": 200, "landmarks": None},
        {"time_sec": 0.066, "center_x": 120, "center_y": 200, "landmarks": None},
    ]
    frame_width = 640
    frame_height = 480

    stats = compute_stats(frame_data, frame_width, frame_height)

    assert stats.total_distance_meters > 0
    assert stats.avg_speed_mps > 0
    assert 0 <= stats.court_coverage_pct <= 100
    assert stats.estimated_shot_count >= 0
    assert len(stats.movement_over_time) > 0


def test_compute_stats_stationary():
    frame_data = [
        {"time_sec": 0.0, "center_x": 100, "center_y": 200, "landmarks": None},
        {"time_sec": 0.033, "center_x": 100, "center_y": 200, "landmarks": None},
    ]
    stats = compute_stats(frame_data, 640, 480)
    assert stats.total_distance_meters == 0.0
    assert stats.avg_speed_mps == 0.0


def test_shot_detection():
    # Simulate wrist acceleration spike
    base_landmarks = [{"name": "RIGHT_WRIST", "x": 100, "y": 100, "z": 0, "visibility": 0.9}]
    spike_landmarks = [{"name": "RIGHT_WRIST", "x": 200, "y": 100, "z": 0, "visibility": 0.9}]

    frame_data = [
        {"time_sec": 0.0, "center_x": 100, "center_y": 200, "landmarks": base_landmarks},
        {"time_sec": 0.033, "center_x": 100, "center_y": 200, "landmarks": base_landmarks},
        {"time_sec": 0.066, "center_x": 100, "center_y": 200, "landmarks": spike_landmarks},
        {"time_sec": 0.1, "center_x": 100, "center_y": 200, "landmarks": base_landmarks},
        {"time_sec": 0.133, "center_x": 100, "center_y": 200, "landmarks": base_landmarks},
    ]
    stats = compute_stats(frame_data, 640, 480)
    assert stats.estimated_shot_count >= 1
