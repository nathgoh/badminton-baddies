import numpy as np

def estimate_pose(frame: np.ndarray, bbox: tuple[float, float, float, float]) -> list[dict] | None:
    """Placeholder pose estimation function.
    
    Args:
        frame: Full video frame (BGR).
        bbox: (x, y, width, height) of the person region.

    Returns:
        None for now - pose estimation requires additional model setup.
    """
    # TODO: Implement proper MediaPipe pose estimation
    # For now, return None to allow basic tracking to work
    return None
