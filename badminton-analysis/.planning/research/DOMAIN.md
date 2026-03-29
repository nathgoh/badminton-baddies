# Domain Research: Badminton AI Analysis Tool

**Researched:** 2026-03-29
**Overall confidence:** HIGH (landmark names and connections verified directly from installed mediapipe 0.10.x package)

---

## 1. MediaPipe Pose — Landmark Map, Output Format, and Best Practices

### 1.1 Authoritative Landmark Names (verified from installed package)

Source: `mediapipe/tasks/python/vision/pose_landmarker.py` — `PoseLandmark(enum.IntEnum)`.

The installed package is the new **MediaPipe Tasks API** (not the deprecated `mediapipe.solutions.pose`). Landmark names are strings like `"NOSE"`, `"LEFT_SHOULDER"`, not `"LANDMARK_0"` or `"LANDMARK_N"`.

```
Index  Name
  0    NOSE
  1    LEFT_EYE_INNER
  2    LEFT_EYE
  3    LEFT_EYE_OUTER
  4    RIGHT_EYE_INNER
  5    RIGHT_EYE
  6    RIGHT_EYE_OUTER
  7    LEFT_EAR
  8    RIGHT_EAR
  9    MOUTH_LEFT
 10    MOUTH_RIGHT
 11    LEFT_SHOULDER
 12    RIGHT_SHOULDER
 13    LEFT_ELBOW
 14    RIGHT_ELBOW
 15    LEFT_WRIST
 16    RIGHT_WRIST
 17    LEFT_PINKY
 18    RIGHT_PINKY
 19    LEFT_INDEX
 20    RIGHT_INDEX
 21    LEFT_THUMB
 22    RIGHT_THUMB
 23    LEFT_HIP
 24    RIGHT_HIP
 25    LEFT_KNEE
 26    RIGHT_KNEE
 27    LEFT_ANKLE
 28    RIGHT_ANKLE
 29    LEFT_HEEL
 30    RIGHT_HEEL
 31    LEFT_FOOT_INDEX
 32    RIGHT_FOOT_INDEX
```

**Key landmarks for badminton analysis:**
- Racket arm: index 15 (LEFT_WRIST), 16 (RIGHT_WRIST), 13 (LEFT_ELBOW), 14 (RIGHT_ELBOW), 11 (LEFT_SHOULDER), 12 (RIGHT_SHOULDER)
- Hips/center of mass: 23 (LEFT_HIP), 24 (RIGHT_HIP)
- Lower body/footwork: 25 (LEFT_KNEE), 26 (RIGHT_KNEE), 27 (LEFT_ANKLE), 28 (RIGHT_ANKLE), 29 (LEFT_HEEL), 30 (RIGHT_HEEL), 31 (LEFT_FOOT_INDEX), 32 (RIGHT_FOOT_INDEX)

### 1.2 Output Format (NormalizedLandmark)

Source: `mediapipe/tasks/python/components/containers/landmark.py`

```python
@dataclasses.dataclass
class NormalizedLandmark:
    x: Optional[float]         # normalized [0.0, 1.0] — multiply by frame width for pixel coords
    y: Optional[float]         # normalized [0.0, 1.0] — multiply by frame height for pixel coords
    z: Optional[float]         # depth relative to hip midpoint; negative = closer to camera
    visibility: Optional[float]  # sigmoid score: landmark visible and not occluded
    presence: Optional[float]    # sigmoid score: landmark present on screen (in-frame)
    name: Optional[str]          # e.g. "NOSE", "LEFT_WRIST" — filled only in some contexts
```

`pose_world_landmarks` uses `Landmark` (same fields but in real-world meters, origin at hip midpoint). Use world landmarks for angle and distance calculations because they are scale-invariant.

The Tasks API result structure:

```python
result: PoseLandmarkerResult
result.pose_landmarks        # list[list[NormalizedLandmark]] — one inner list per detected pose
result.pose_world_landmarks  # list[list[Landmark]] — same, in world coordinates
```

For single-player tracking, always index with `result.pose_landmarks[0]` and check `len(result.pose_landmarks) > 0`.

### 1.3 Correct Running Mode for Video Processing

The Tasks API has three running modes. For batch video file processing, use **VIDEO mode** (`VisionTaskRunningMode.VIDEO`):

```python
from mediapipe.tasks.python.vision.core.vision_task_running_mode import VisionTaskRunningMode
from mediapipe.tasks.python.vision.pose_landmarker import PoseLandmarker, PoseLandmarkerOptions
from mediapipe.tasks.python.core.base_options import BaseOptions

options = PoseLandmarkerOptions(
    base_options=BaseOptions(model_asset_path="pose_landmarker_full.task"),
    running_mode=VisionTaskRunningMode.VIDEO,
    num_poses=1,
    min_pose_detection_confidence=0.5,
    min_pose_presence_confidence=0.5,
    min_tracking_confidence=0.5,
    output_segmentation_masks=False,
)

with PoseLandmarker.create_from_options(options) as landmarker:
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_idx = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        timestamp_ms = int((frame_idx / fps) * 1000)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        result = landmarker.detect_for_video(mp_image, timestamp_ms)
        frame_idx += 1
    cap.release()
```

**Why VIDEO mode, not IMAGE mode:** VIDEO mode enables temporal smoothing and tracking across frames. The `timestamp_ms` values must be monotonically increasing. IMAGE mode detects independently per frame — jitter is worse and tracking IDs reset.

### 1.4 Confidence Filtering Best Practices

- **Visibility threshold:** 0.5 is the library default (verified in `drawing_utils.py`). For sports analysis, 0.65 is better for upper-body joints where occlusion from the racket arm is common.
- **Presence threshold:** Also 0.5 default. Landmarks near the frame edge score low here. Filter out before computing angles.
- **Frame-level confidence:** If fewer than N key landmarks pass the threshold, skip the frame entirely rather than computing angles from partial data.
- **Missing frame handling:** Store `None` for frames with no reliable pose. The existing `_detect_shots` code already handles `None` wrist positions — this pattern is correct.
- **Temporal smoothing:** Apply a simple moving average (window=3 frames) on landmark coordinates after extraction. This removes single-frame noise without introducing the latency of a Kalman filter.

### 1.5 Pixel Coordinate Conversion

NormalizedLandmark x/y are in [0,1]. Convert explicitly:

```python
px = int(landmark.x * frame_width)
py = int(landmark.y * frame_height)
```

The `drawing_utils.py` `_normalized_to_pixel_coordinates` function clips at `image_width - 1` / `image_height - 1` using `math.floor`. Never use `lm["x"]` directly as a pixel coordinate — the current code in `analysis.py` does this for wrist speed which is technically correct (produces normalized-space distances), but the values fed to `_draw_skeleton` must be scaled to pixel space first.

### 1.6 Model File

The Tasks API requires a `.task` bundle file, not a `.tflite` file directly. Available models:
- `pose_landmarker_lite.task` — fastest, lowest accuracy
- `pose_landmarker_full.task` — balanced (recommended for this project)
- `pose_landmarker_heavy.task` — highest accuracy, ~3x slower

For club video analysis (non-real-time), use **full**. Download from `https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_full/float16/latest/pose_landmarker_full.task`.

---

## 2. The Skeleton Rendering Bug — Root Cause and Fix

### 2.1 What Is Wrong

In `services/analysis.py`, `_draw_skeleton` builds a lookup `lm_map = {lm["name"]: ...}` and then looks up keys like `"LANDMARK_0"`, `"LANDMARK_1"`, etc.:

```python
start_name = f"LANDMARK_{start_idx}"
end_name = f"LANDMARK_{end_idx}"
if start_name in lm_map and end_name in lm_map:
    ...
```

MediaPipe's `NormalizedLandmark.name` field is populated with values like `"NOSE"`, `"LEFT_SHOULDER"`, or may be `None` if not explicitly set. It is never `"LANDMARK_0"`. The lookup always fails. Zero skeleton lines are ever drawn.

### 2.2 The Correct Fix

Landmarks should be stored and accessed by **index** (their position in the list), not by a name key. The connections in `PoseLandmarksConnections.POSE_LANDMARKS` are defined as `(start_idx, end_idx)` integer pairs:

```python
# Correct approach: store by index
lm_map = {}
for idx, lm in enumerate(landmarks):
    if lm.get("visibility", 0) > 0.5:
        px = int(lm["x"] * frame_width)
        py = int(lm["y"] * frame_height)
        lm_map[idx] = (px, py)

# Connections use integer indices directly
connections = [
    (0,1),(1,2),(2,3),(3,7),
    (0,4),(4,5),(5,6),(6,8),
    (9,10),(11,12),(11,13),(13,15),(15,17),(15,19),(15,21),(17,19),
    (12,14),(14,16),(16,18),(16,20),(16,22),(18,20),
    (11,23),(12,24),(23,24),(23,25),(24,26),(25,27),(26,28),
    (27,29),(28,30),(29,31),(30,32),(27,31),(28,32),
]
for start_idx, end_idx in connections:
    if start_idx in lm_map and end_idx in lm_map:
        cv2.line(frame, lm_map[start_idx], lm_map[end_idx], color, 2)
```

The connection list above is taken directly from `PoseLandmarksConnections.POSE_LANDMARKS` in the installed package. It includes hand connections (15→17, 15→19, 15→21, 17→19, 16→18, 16→20, 16→22, 18→20) that the current code's connection list misses — these matter because the wrist/hand region is the most important for shot mechanics.

### 2.3 Landmark Data Schema for Storage

When serializing landmarks per frame to JSON/dict, use index-based storage:

```python
{
    "frame_idx": 42,
    "time_sec": 1.4,
    "landmarks": [
        {"idx": 0,  "name": "NOSE",         "x": 0.51, "y": 0.12, "z": -0.08, "visibility": 0.99, "presence": 0.98},
        {"idx": 11, "name": "LEFT_SHOULDER", "x": 0.44, "y": 0.28, "z": -0.02, "visibility": 0.95, "presence": 0.97},
        # ... all 33
    ]
}
```

Keep both `idx` and `name` in the stored dict. Use `idx` for skeleton connections. Use `name` for sport-specific lookups in analysis code. Do not rely on the MediaPipe `NormalizedLandmark.name` field being populated — populate it yourself from the `PoseLandmark` enum.

---

## 3. Player Tracking — Isolating One Player After Click-Select

### 3.1 Current Architecture

The current `tracking.py` uses IoU-based overlap matching to re-identify a bounding box across frames. The selected bbox from frame 0 is propagated forward by matching it against YOLO detections each frame. IoU threshold is 0.2 (very permissive).

This works for simple cases but breaks when:
- Players cross or occlude (IoU drops to 0 between target and nearest detection)
- Player is briefly off-frame
- YOLO misses the player for a few frames

### 3.2 Recommended Approach: IoU + Center Distance Fallback

Extend the current tracker to use center-point distance as a fallback when IoU fails:

```python
def track_person_in_frame(prev_box, candidates, iou_threshold=0.2, max_center_distance_px=150):
    # First try IoU
    best_iou_match = find_best_iou(prev_box, candidates, iou_threshold)
    if best_iou_match:
        return best_iou_match

    # Fallback: nearest center
    prev_cx = prev_box.x + prev_box.width / 2
    prev_cy = prev_box.y + prev_box.height / 2
    best = min(candidates, key=lambda c: center_dist(c, prev_cx, prev_cy), default=None)
    if best and center_dist(best, prev_cx, prev_cy) < max_center_distance_px:
        return best
    return None  # lost — hold last known position for N frames before giving up
```

### 3.3 Click-Select UX — Coordinate System Bug

The current `SelectPage.tsx` hardcodes 640 and 480:

```tsx
left: `${(person.x / 640) * 100}%`,
top:  `${(person.y / 480) * 100}%`,
```

This means the bounding box overlay is drawn at the wrong position for any video that is not exactly 640×480. The detect endpoint must return the actual frame dimensions, or the frontend must use the rendered image dimensions via a `ref` on the `<img>` element. The backend should include `frame_width` and `frame_height` in `DetectResponse`.

### 3.4 Person Selection Mapping to Pose

After click-select, the selected `person_bbox` from YOLO is used as the anchor for tracking. When running MediaPipe pose estimation, crop the frame to the bbox (with 20% padding) before passing to the landmarker. This improves accuracy on broadcasts where players are small relative to full frame:

```python
pad = 0.2
x1 = max(0, int(bbox.x - bbox.width * pad))
y1 = max(0, int(bbox.y - bbox.height * pad))
x2 = min(frame.shape[1], int(bbox.x + bbox.width * (1 + pad)))
y2 = min(frame.shape[0], int(bbox.y + bbox.height * (1 + pad)))
crop = frame[y1:y2, x1:x2]
```

Scale returned landmark coordinates back to full-frame pixel space after detection.

### 3.5 Multi-Person Disambiguation

MediaPipe `num_poses=1` does **not** guarantee it picks the correct player when two players are in frame — it picks the highest-confidence detection, which may be the opponent. Options:

1. **Crop-first (recommended):** Run MediaPipe only on the cropped bbox region as described above. With `num_poses=1` on a tight crop, it can only detect the target player.
2. **Overlap selection:** Run with `num_poses=2`, then select the pose whose hip midpoint falls inside the tracked bbox.

Approach 1 is simpler and more reliable for this use case.

---

## 4. Movement Analysis — Heatmaps and Footwork

### 4.1 Court Coverage Heatmap

The current grid-based coverage counter (20×20 cells) is functional but produces only a percentage — it throws away spatial information. For a coaching heatmap visualization, accumulate a 2D histogram of player foot positions across the analysis window:

```python
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.cm as cm

def build_heatmap(positions: list[tuple[float, float]],
                  frame_width: int, frame_height: int,
                  grid_size: int = 40) -> np.ndarray:
    # positions are (center_x_px, center_y_px) tuples
    heatmap = np.zeros((grid_size, grid_size), dtype=np.float32)
    for cx, cy in positions:
        col = int((cx / frame_width) * grid_size)
        row = int((cy / frame_height) * grid_size)
        col = min(max(col, 0), grid_size - 1)
        row = min(max(row, 0), grid_size - 1)
        heatmap[row, col] += 1

    # Gaussian smooth for visual quality
    from scipy.ndimage import gaussian_filter
    heatmap = gaussian_filter(heatmap, sigma=1.5)
    return heatmap
```

Render as a translucent overlay on a court diagram PNG. The output should be a base64-encoded PNG served alongside the annotated video URL in `AnalysisResult`.

**Court calibration caveat:** The current `COURT_LENGTH_M = 13.4` approach assumes the full frame height equals the court. For broadcast video, the court occupies a portion of the frame. A proper calibration step (click the four court corners) is out of scope for v1 but should be flagged as a future requirement. For v1, document the assumption clearly.

### 4.2 Footwork Detection from Pose Landmarks

Use ankle and heel positions (indices 27–32) rather than bounding box center for footwork tracking — they are more stable and positioned closer to the actual court surface.

**Key footwork patterns for badminton:**

| Pattern | Detection Signal |
|---------|-----------------|
| Lunge (forehand) | Right ankle far right, knee bent (angle < 120°), left foot behind |
| Lunge (backhand) | Left ankle far left, knee bent |
| Jump smash | Both ankles above typical ground line for ≥3 consecutive frames |
| Split step | Both feet symmetric, brief upward then downward movement |
| Recovery to base | Left hip/right hip midpoint approaching center court position |
| Side shuffle | Lateral displacement between frames > threshold, minimal vertical movement |

Implement as rule-based classifiers over a sliding window of 5–10 frames after pose data is available. Full ML footwork classification is out of scope for v1.

**Ankle velocity** as a footwork intensity proxy:
```python
ankle_velocity = sqrt((ankle_x[t] - ankle_x[t-1])^2 + (ankle_y[t] - ankle_y[t-1])^2) / dt
```
Use normalized coordinates (0–1) so velocity is scale-independent across different video resolutions. Spikes > 0.05/frame indicate explosive movement.

### 4.3 Body Center of Mass Approximation

Use the hip midpoint as a center-of-mass proxy for movement analysis:

```python
hip_cx = (lm[23].x + lm[24].x) / 2 * frame_width
hip_cy = (lm[23].y + lm[24].y) / 2 * frame_height
```

This is more stable than the bounding box centroid (which wobbles with arm swing) and more meaningful for court coverage analysis. Replace the `center_x`/`center_y` in `frame_data` with hip midpoint when pose is available.

---

## 5. Shot Mechanics Analysis from Pose Landmarks

### 5.1 Joint Angle Computation

All angle calculations should use **world landmarks** (`pose_world_landmarks`), not normalized image landmarks. World landmarks are in meters relative to hip center, making angles invariant to camera distance and body scale:

```python
import numpy as np

def compute_angle(a: tuple, b: tuple, c: tuple) -> float:
    """
    Compute angle at joint B formed by vectors BA and BC.
    a, b, c are (x, y, z) tuples in world coordinates.
    Returns angle in degrees.
    """
    ba = np.array(a) - np.array(b)
    bc = np.array(c) - np.array(b)
    cos_angle = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc) + 1e-8)
    return float(np.degrees(np.arccos(np.clip(cos_angle, -1.0, 1.0))))
```

### 5.2 Key Angles for Badminton Stroke Analysis

**Elbow angle at contact** (most important for overhead shots):
- Joint B = elbow (idx 14 for right-handed player)
- Point A = wrist (idx 16)
- Point C = shoulder (idx 12)
- Good overhead contact: 150–180° (near full extension)
- Poor contact: < 130° (bent arm, loss of power)

**Shoulder rotation** (torso contribution to smash):
- Angle between shoulder line and hip line, viewed in top-down projection (use x/z world coords)
- Full rotation: 30–60° shoulder-over-hip at contact
- Poor rotation: < 15° (hitting with arm only)

**Knee bend during lunge** (footwork quality):
- Joint B = knee (idx 26 right, idx 25 left)
- Point A = hip (idx 24 right, idx 23 left)
- Point C = ankle (idx 28 right, idx 27 left)
- Good low lunge: 70–110°
- High standing lunge: > 140° (poor balance and reach)

**Wrist elevation at contact**:
- Compare wrist y-coordinate to shoulder y-coordinate in normalized space
- Overhead clear/smash: wrist y < shoulder y (wrist is above shoulder in image)
- Net kill: wrist y ≈ shoulder y or slightly above

**Hip height** (body posture):
- Average hip y-coordinate in normalized space
- Lower hips (larger y value) = lower stance = better badminton posture
- Club player baseline: hips consistently high (poor posture)

### 5.3 Shot Detection from Wrist Acceleration

The existing `_detect_shots` approach (wrist speed spike detection) is functionally reasonable. Improvements:

- Use **right wrist speed** specifically (not max of left/right) for right-handed player — or ask user to designate dominant hand
- Combine with **elbow angle change rate**: shots show rapid extension → contraction → extension cycle
- Add **minimum contact height filter**: ignore wrist speed spikes when wrist y > 0.7 (low pick-ups are different from smashes/clears)
- Classify shot type:
  - Overhead = wrist y < 0.3 at peak speed
  - Net = wrist y > 0.5 at peak speed
  - Mid-court = 0.3 ≤ wrist y ≤ 0.5

### 5.4 Scoring Algorithm

Convert continuous measurements to 0–10 scores for the coaching dashboard:

```python
def score_elbow_extension(angle_at_contact: float) -> float:
    """Scores overhead elbow extension. 10 = full extension (165°+)."""
    if angle_at_contact >= 165:
        return 10.0
    elif angle_at_contact >= 145:
        return 7.0 + (angle_at_contact - 145) / 20 * 3
    elif angle_at_contact >= 120:
        return 4.0 + (angle_at_contact - 120) / 25 * 3
    else:
        return max(0.0, angle_at_contact / 120 * 4)

def score_court_coverage(coverage_pct: float) -> float:
    """Scores court coverage. 10 = 70%+ covered."""
    return min(10.0, (coverage_pct / 70) * 10)

def score_footwork(avg_ankle_speed: float) -> float:
    """Proxy: higher average ankle velocity = more active footwork."""
    return min(10.0, avg_ankle_speed / 0.04 * 10)
```

These scoring functions are heuristics designed for club-level players and should be documented as such in the UI.

### 5.5 AI Coaching Notes Generation

The coached text should be derived from the computed metrics, not from a general-purpose LLM call with no grounding. Structure:

1. Compute numeric metrics (elbow angle, shoulder rotation, knee bend, etc.)
2. Map metrics to finding categories: `["good", "needs_work", "critical"]`
3. Use a template-based generator for v1, or pass structured metrics as context to an LLM call

Template approach for v1 (no external API dependency):

```python
COACHING_TEMPLATES = {
    "elbow_low": "Your elbow angle at contact is averaging {angle:.0f}°. Aim for 150°+ on overhead shots to generate more power. Practice shadow-swinging with a focus on full arm extension at the point of contact.",
    "footwork_passive": "Your ankle movement data suggests limited explosive footwork. Your average displacement per frame is {vel:.3f} normalized units. Work on split-step timing after each shot to improve court coverage.",
    "coverage_low": "You covered {pct:.0f}% of the court in this analysis window. Club-level targets are 50–70%. Focus on recovering to base position (center-T) after each shot.",
}
```

LLM integration (optional, later): Pass the computed metrics as a structured prompt to an LLM API (OpenAI, Anthropic) and ask it to generate personalized coaching text. This is an easy add-on once metrics are reliable.

---

## 6. Video Pipeline Pitfalls

### 6.1 VideoCapture Resource Management

**Current bug:** The analysis router opens and closes `cv2.VideoCapture` once per frame in a seek-per-frame pattern. This is because `extract_frame` opens, seeks, reads, and closes independently.

**Fix:** Open `cv2.VideoCapture` once per analysis run and iterate sequentially. For the `render_annotated_video` function this is already correct. The issue is in `detect_persons` / `extract_frame` being called repeatedly in a loop — do not call `extract_frame` inside the analysis loop.

**VideoCapture gotcha:** `cap.set(cv2.CAP_PROP_POS_FRAMES, n)` is unreliable for certain codecs (H.264, HEVC) because they have keyframe dependencies. Seeking to arbitrary frames can land on the wrong frame. Prefer sequential read unless seeking is unavoidable.

### 6.2 Annotated Video Codec and Browser Compatibility

The current code uses `cv2.VideoWriter_fourcc(*"mp4v")`. This produces MPEG-4 Part 2 (not H.264). Most modern browsers cannot play raw `mp4v` video inline.

**Fix:** Use H.264 encoding. OpenCV on Linux requires the `avc1` fourcc with a `.mp4` container:

```python
fourcc = cv2.VideoWriter_fourcc(*"avc1")
writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
```

If `avc1` is not available in the OpenCV build (common with default `opencv-python`), fall back to writing frames as `mp4v` then transcoding with `ffmpeg` as a subprocess:

```python
import subprocess
subprocess.run([
    "ffmpeg", "-y", "-i", temp_path,
    "-vcodec", "libx264", "-crf", "23", "-preset", "fast",
    "-pix_fmt", "yuv420p",
    output_path
], check=True)
```

`yuv420p` is required for broad browser compatibility. Many encoders default to `yuv444p` which browsers do not support.

### 6.3 Frame Processing Order and Memory

Processing a full video frame-by-frame with both YOLO tracking and MediaPipe pose extraction in memory will be slow for long videos. For a club match (~20 min), a 30fps video has ~36,000 frames. Do not store all frames in memory.

**Pipeline design:**

```
Open VideoCapture (once)
For each frame:
  1. Read frame
  2. YOLO detect → get candidate bboxes
  3. Track: match to selected player's last bbox
  4. Crop tracked bbox with padding
  5. MediaPipe pose on crop
  6. Serialize: store (frame_idx, time_sec, hip_cx, hip_cy, landmarks_list) in a list
  7. Write annotated frame to VideoWriter immediately — do not buffer
Close VideoCapture
Close VideoWriter
Run compute_stats on the serialized list
```

This keeps peak memory proportional to a single frame, not the entire video.

### 6.4 Frame Sampling for Long Videos

Processing every frame at 30fps for pose estimation is expensive. Consider:
- **Analysis stride:** Run pose estimation every 3rd frame (10fps effective), interpolate between
- **Annotated video:** Still write every frame, but use the most recently computed landmarks for frames that weren't analyzed
- **Trade-off:** Footwork events shorter than 100ms (3 frames at 30fps) may be missed. This is acceptable for club-level coaching feedback.

### 6.5 Progress Reporting

The analysis job is a long-running background task. The current `AnalysisStatus` schema has a `progress: float | None` field but it is never set. For good UX, report progress as `frame_idx / total_frames`. Use the existing polling mechanism (`GET /api/analyze/{id}/status`). The status dict should be updated after every N frames (e.g., every 50 frames) to avoid lock contention on the shared dict.

### 6.6 Output Video Frame Dimensions

`cv2.VideoWriter` must receive frames with **exactly** the dimensions passed to its constructor. If the annotated frame is drawn at different dimensions (e.g., because of a crop operation that was not properly undone), the writer silently drops frames. Always verify output frame shape before writing.

### 6.7 OpenCV BGR vs RGB

- OpenCV reads frames in BGR
- MediaPipe Tasks API requires RGB input: `mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))`
- Always convert to RGB before passing to MediaPipe and convert back to BGR before writing with OpenCV
- Forgetting this results in inverted colors on the skeleton overlay (visible but confusing)

### 6.8 SelectPage Coordinate System Fix

The frontend `SelectPage.tsx` uses hardcoded 640/480 for bounding box overlay positions. The backend `DetectResponse` must include actual frame dimensions so the frontend can position bboxes accurately:

```typescript
interface DetectResponse {
    frame_image: string;
    persons: BoundingBox[];
    frame_width: number;   // ADD THIS
    frame_height: number;  // ADD THIS
}
```

Frontend calculation then becomes:
```tsx
left: `${(person.x / frameWidth) * 100}%`,
top:  `${(person.y / frameHeight) * 100}%`,
```

---

## 7. Architecture for the Analysis Pipeline

### 7.1 Recommended Component Structure

```
analysis_pipeline/
  frame_extractor.py     # OpenCV capture, sequential frame iteration
  tracker.py             # IoU + center-distance person re-identification (extends current)
  pose_estimator.py      # MediaPipe Tasks API wrapper, crop-then-estimate pattern
  feature_extractor.py   # Per-frame feature extraction (landmarks → angles, velocities)
  stats_builder.py       # Aggregate features into AnalysisStats (extends current)
  heatmap_builder.py     # 2D histogram → smoothed heatmap PNG
  shot_classifier.py     # Wrist speed + elbow angle → shot events
  mechanics_scorer.py    # Per-shot angle → 0-10 scores
  coaching_notes.py      # Metric thresholds → coaching text
  video_renderer.py      # cv2.VideoWriter, skeleton overlay (fix current)
```

This separates concerns and makes each component independently testable, which is currently a gap.

### 7.2 Data Contract Between Components

All components should pass data through a single `FrameData` structure:

```python
@dataclasses.dataclass
class FrameData:
    frame_idx: int
    time_sec: float
    bbox: BoundingBox | None          # tracked player bbox in full-frame coords
    landmarks: list[dict] | None      # 33-element list, index-aligned, full-frame normalized coords
    world_landmarks: list[dict] | None  # 33-element list, world coords in meters
    hip_cx: float | None              # derived from landmarks[23] + landmarks[24]
    hip_cy: float | None
```

### 7.3 Heatmap as a First-Class Output

Add `heatmap_image_url` to `AnalysisResult` alongside `annotated_video_url`. The heatmap is a PNG (court diagram with player positions overlaid as a heat gradient). This is a dashboard element the `ResultsPage.tsx` should display.

```python
class AnalysisResult(BaseModel):
    stats: AnalysisStats
    annotated_video_url: str
    heatmap_image_url: str           # ADD
    mechanics_scores: MechanicsScores  # ADD
    coaching_notes: list[str]        # ADD
```

---

## 8. Confidence Assessment

| Area | Confidence | Basis |
|------|------------|-------|
| MediaPipe landmark names and indices | HIGH | Verified from installed `pose_landmarker.py` in `.venv` |
| MediaPipe Tasks API structure | HIGH | Read from installed package source directly |
| Skeleton bug root cause and fix | HIGH | Code read directly; bug is definitively confirmed |
| Connection list correctness | HIGH | Copied directly from `PoseLandmarksConnections.POSE_LANDMARKS` |
| Video codec browser compat | HIGH | Well-established cv2/H.264 constraint |
| Badminton joint angles for good form | MEDIUM | Based on sports biomechanics training data; no specific paper cited |
| Footwork pattern detection rules | MEDIUM | Domain knowledge; no peer-reviewed source verified |
| Heatmap smoothing parameters | MEDIUM | Standard Gaussian sigma recommendations, training data |
| LLM coaching notes approach | MEDIUM | Template-first is standard practice; LLM integration details unverified |

---

## 9. Phase Implications

### What must be fixed before any feature work is meaningful

1. **Skeleton rendering bug** — `_draw_skeleton` must switch from name-string lookup to integer index lookup. Until this is fixed, no visual output validates that pose data is being generated correctly.

2. **Pose estimation stub** — `services/pose.py` returns `None`. This must be implemented before any analysis metrics can be computed or tested.

3. **H.264 output** — `mp4v` output will not play in the browser. This must be fixed before the results page can show the annotated video.

### What is immediately buildable once the above are fixed

- Shot count improvement (dominant hand, height filter)
- Hip-based movement tracking (replacing bbox centroid)
- Heatmap PNG generation
- Elbow angle scoring for overhead shots
- Template-based coaching notes

### What needs a research spike before implementation

- Court calibration / homography for accurate meter distances (out of scope v1 but needed for honest distance reporting)
- LLM coaching notes integration (API key management, prompt design)
- Side-by-side comparison feature (data model for "ideal form" reference)

---

## 10. Sources

- `backend/.venv/lib/python3.12/site-packages/mediapipe/tasks/python/vision/pose_landmarker.py` — authoritative landmark enum and connections
- `backend/.venv/lib/python3.12/site-packages/mediapipe/tasks/python/components/containers/landmark.py` — NormalizedLandmark and Landmark field definitions
- `backend/.venv/lib/python3.12/site-packages/mediapipe/tasks/python/vision/drawing_utils.py` — visibility/presence thresholds, pixel coordinate conversion
- `backend/.venv/lib/python3.12/site-packages/mediapipe/tasks/python/vision/drawing_styles.py` — canonical left/right landmark sets
- `backend/services/analysis.py` — confirmed skeleton bug (lines 182–186)
- `backend/services/pose.py` — confirmed stub returning `None`
- `backend/services/tracking.py` — confirmed IoU-only tracking with 0.2 threshold
- `frontend/src/pages/SelectPage.tsx` — confirmed 640/480 hardcode (lines 46–49)
- `frontend/src/types/index.ts` — confirmed missing frame_width/frame_height in DetectResponse
- `.planning/codebase/CONCERNS.md` — pre-existing technical debt catalog
- `.planning/PROJECT.md` — project scope and constraints
