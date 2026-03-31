# Annotated Report Clips Design

## Summary

Add server-rendered annotated report clips for the existing report windows so the user can review
the tracked player with a stick-figure overlay directly in the report. The backend should render
short MP4 artifacts from the local source video for shot-selection events and shuttle pressure
windows, then expose those artifacts through the API. The frontend should prefer the annotated
clip in a native video player and fall back to the current YouTube embed when rendering is
unavailable.

## Goals

- Show the selected player with the tracking box and stick-figure overlay in report clips.
- Reuse the existing shot-event and shuttle-pressure clip windows instead of inventing new clip
  selection UI.
- Keep report playback fast by rendering only short report windows, not the full source video.
- Preserve the current report experience when clip rendering is unavailable by falling back to the
  YouTube embed.
- Keep the implementation aligned with the current media artifact pipeline and in-memory analysis
  lifecycle.

## Non-Goals

- Rendering a fully annotated export of the entire source video.
- Replacing the current live processing frame feed.
- Adding timeline editing or user-defined clip trimming in the frontend.
- Building client-side pose synchronization on top of the YouTube iframe.
- Guaranteeing frame-perfect skeleton coverage in windows with sparse pose detections.

## Current Constraints

- The backend already stores local source video paths through the media artifact pipeline.
- The report already has clip windows for shot events and shuttle pressure windows.
- The live processing path already emits annotated pose frames with a selected-player box and
  stick-figure overlay.
- The report screen currently uses a shared YouTube iframe player, not backend-served media.
- Analyses are stored in memory, so clip metadata must remain derivable from the current
  `AnalysisRecord` and local artifact directory.

## Architecture

### 1. Annotated Clip Artifact Builder

Extend the media artifact pipeline with a clip-rendering capability that accepts:

- `analysis_id`
- the local `source_video_path`
- clip window bounds in seconds
- pose frames and tracking samples for the selected player
- a clip identifier for stable file naming

The renderer should write short MP4 clips into the analysis artifact directory and return the file
path plus media type. Rendering should overlay:

- the selected-player bounding box when a tracked sample is available
- the stick-figure skeleton when pose landmarks are available for that frame
- optional stage text or frame counters are out of scope for the report clips

The implementation should prefer the existing local Python/OpenCV drawing path for overlays and use
ffmpeg only for extracting/encoding clip windows where needed.

### 2. Report Clip Metadata

Extend shot-selection events and shuttle pressure windows with optional rendered-clip metadata:

- `rendered_clip_url: str | None`
- `rendered_clip_media_type: str | None`

Keep the existing `clip_start_seconds` and `clip_end_seconds` fields unchanged. Those fields remain
the fallback contract for the YouTube player and the windowing logic.

### 3. Service Integration

After analytics and evidence are assembled, but before the final report is stored, the service
should attempt to render annotated clips for:

- every shot-selection event
- every shuttle pressure window with valid clip bounds

If clip rendering succeeds, the service should inject the rendered clip URL into the report-ready
analytics data. If it fails, the service should:

- append a warning to the analysis record
- leave rendered clip fields empty
- preserve the rest of the report

Rendering failure must never fail the entire analysis.

### 4. API Surface

Add a new file-serving route for report clip artifacts under the existing analysis namespace, for
example:

- `GET /api/analyses/{analysis_id}/clips/{clip_id}`

The route should validate ownership the same way other analysis resources do, resolve the artifact
from the current analysis directory, and return a `FileResponse`.

### 5. Frontend Clip Viewer

Keep the shared clip-viewer pattern in the analytics tab, but change the player selection logic:

- if `rendered_clip_url` is available, render an HTML `<video>` player
- otherwise, keep using the current shared YouTube iframe

The clip cards should keep the existing “Load clip” interaction. The viewer should label the active
asset clearly, for example:

- `Annotated clip`
- `YouTube fallback`

This keeps the user-facing behavior simple while making the backend-generated evidence the primary
experience.

## Data Model Changes

### Shot Selection Events

Extend `ShotSelectionEvent` with:

- `rendered_clip_url: str | None = None`
- `rendered_clip_media_type: str | None = None`

### Shuttle Pressure Windows

Extend `PressureWindow` with:

- `rendered_clip_url: str | None = None`
- `rendered_clip_media_type: str | None = None`

### Internal Analysis Data

If needed for wiring and file resolution, the analysis record may carry transient clip artifact
metadata, but the main source of truth for the frontend should stay the final report payload.

## Rendering Strategy

### Overlay Inputs

Annotated clip rendering should draw from:

- focused player tracking samples for box placement
- stored pose frames for skeleton joints and connections

The renderer should align samples to video time with nearest-sample matching. If a frame lacks pose
or tracking data, the renderer should still output the frame without that layer instead of dropping
or failing the clip.

### Clip Scope

Only render short report windows that already exist:

- shot event windows
- shuttle pressure windows

This keeps compute bounded and avoids generating artifacts the user never opens.

## Failure Handling

If annotated rendering fails because of missing source media, missing ffmpeg, sparse pose data, or
other runtime issues:

- keep the report valid
- keep clip bounds intact
- leave `rendered_clip_url` empty
- append a warning for visibility
- let the frontend fall back to the YouTube embed automatically

## Testing Strategy

### Backend

- Add API tests proving report events and pressure windows can include rendered clip URLs.
- Add API tests for the new clip file-serving route.
- Add tests proving rendering failure degrades gracefully to empty rendered clip fields plus
  warnings.
- Add pipeline tests for clip metadata generation and stable artifact naming.

### Frontend

- Add tests proving the shared report viewer prefers a native `<video>` player when a rendered clip
  URL is present.
- Add tests proving the existing YouTube iframe remains the fallback when rendered clips are
  absent.
- Add tests proving the clip label changes based on the active asset type.

## Recommended Delivery Slice

1. Extend report models with optional rendered clip metadata.
2. Add media-pipeline support for short annotated clip rendering and cleanup.
3. Add a backend route for serving rendered report clips.
4. Inject rendered clip URLs into shot events and pressure windows during report assembly.
5. Update the frontend shared clip viewer to prefer native video playback.
6. Add backend and frontend tests for the preferred-path and fallback-path behavior.

## Acceptance Criteria

- A completed report can surface backend-rendered annotated clips for shot events and shuttle
  pressure windows.
- Annotated clips show the selected player with the tracking box and stick-figure overlay when that
  evidence is available.
- The frontend prefers rendered clips in a native video player when they exist.
- The frontend falls back to the current YouTube embed when rendered clips are unavailable.
- Clip rendering failures do not fail the overall analysis.
- Backend and frontend tests cover both annotated and fallback playback paths.
