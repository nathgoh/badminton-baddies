from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass(slots=True)
class PreparedMediaArtifacts:
    source_video_path: str
    setup_frame_path: str
    setup_frame_content_type: str
    source_url: str
    video_duration_seconds: float | None = None


class MediaPreparationError(RuntimeError):
    pass


class MediaArtifactPipeline(Protocol):
    def prepare_analysis(self, analysis_id: str, youtube_url: str) -> PreparedMediaArtifacts: ...

    def cleanup_analysis(self, analysis_id: str) -> None: ...


def _mock_setup_frame_svg(analysis_id: str) -> str:
    return f"""
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720">
      <defs>
        <linearGradient id="court" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stop-color="#183221"/>
          <stop offset="100%" stop-color="#2f6a44"/>
        </linearGradient>
      </defs>
      <rect width="1280" height="720" rx="40" fill="#f6ece1" />
      <rect x="170" y="120" width="940" height="480" rx="24" fill="url(#court)" />
      <rect
        x="230"
        y="160"
        width="820"
        height="400"
        rx="18"
        fill="none"
        stroke="#fef7ef"
        stroke-width="8"
      />
      <line x1="640" y1="160" x2="640" y2="560" stroke="#fef7ef" stroke-width="6" />
      <line x1="230" y1="360" x2="1050" y2="360" stroke="#fef7ef" stroke-width="6" />
      <text
        x="96"
        y="96"
        fill="#183221"
        font-size="34"
        font-family="Avenir Next, sans-serif"
      >Setup Frame</text>
      <text
        x="96"
        y="646"
        fill="#183221"
        font-size="24"
        font-family="Avenir Next, sans-serif"
      >Analysis {analysis_id[:8]}</text>
    </svg>
    """.strip()


class MockMediaArtifactPipeline:
    def __init__(self, artifact_root: Path) -> None:
        self._artifact_root = artifact_root

    def prepare_analysis(self, analysis_id: str, youtube_url: str) -> PreparedMediaArtifacts:
        analysis_dir = self._artifact_root / analysis_id
        analysis_dir.mkdir(parents=True, exist_ok=True)

        source_video_path = analysis_dir / "source.mp4"
        source_video_path.write_bytes(b"mock-video")

        setup_frame_path = analysis_dir / "setup-frame.svg"
        setup_frame_path.write_text(_mock_setup_frame_svg(analysis_id), encoding="utf-8")

        return PreparedMediaArtifacts(
            source_video_path=str(source_video_path),
            setup_frame_path=str(setup_frame_path),
            setup_frame_content_type="image/svg+xml",
            source_url=youtube_url,
            video_duration_seconds=120.0,
        )

    def cleanup_analysis(self, analysis_id: str) -> None:
        shutil.rmtree(self._artifact_root / analysis_id, ignore_errors=True)


class ShellMediaArtifactPipeline:
    def __init__(
        self,
        artifact_root: Path,
        *,
        setup_frame_timestamp: str = "00:00:03",
    ) -> None:
        self._artifact_root = artifact_root
        self._setup_frame_timestamp = setup_frame_timestamp

    def prepare_analysis(self, analysis_id: str, youtube_url: str) -> PreparedMediaArtifacts:
        analysis_dir = self._artifact_root / analysis_id
        analysis_dir.mkdir(parents=True, exist_ok=True)

        yt_dlp = shutil.which("yt-dlp")
        if yt_dlp is None:
            raise MediaPreparationError("yt-dlp is not installed.")

        ffmpeg = shutil.which("ffmpeg")
        if ffmpeg is None:
            raise MediaPreparationError("ffmpeg is not installed.")

        output_template = analysis_dir / "source.%(ext)s"
        self._run(
            [
                yt_dlp,
                "--no-playlist",
                "--merge-output-format",
                "mp4",
                "-o",
                str(output_template),
                youtube_url,
            ]
        )

        source_video_path = self._find_source_video(analysis_dir)
        setup_frame_path = analysis_dir / "setup-frame.png"
        self._run(
            [
                ffmpeg,
                "-y",
                "-ss",
                self._setup_frame_timestamp,
                "-i",
                str(source_video_path),
                "-frames:v",
                "1",
                str(setup_frame_path),
            ]
        )

        if not setup_frame_path.exists():
            raise MediaPreparationError("ffmpeg did not produce a setup frame.")

        duration = self._probe_duration(source_video_path, ffmpeg)

        return PreparedMediaArtifacts(
            source_video_path=str(source_video_path),
            setup_frame_path=str(setup_frame_path),
            setup_frame_content_type="image/png",
            source_url=youtube_url,
            video_duration_seconds=duration,
        )

    def cleanup_analysis(self, analysis_id: str) -> None:
        shutil.rmtree(self._artifact_root / analysis_id, ignore_errors=True)

    def _probe_duration(self, video_path: Path, ffmpeg_path: str) -> float | None:
        ffprobe = shutil.which("ffprobe")
        if ffprobe is None:
            # Fall back to ffmpeg's parent dir
            ffprobe = str(Path(ffmpeg_path).parent / "ffprobe")
        try:
            result = subprocess.run(
                [
                    ffprobe,
                    "-v",
                    "error",
                    "-show_entries",
                    "format=duration",
                    "-of",
                    "default=noprint_wrappers=1:nokey=1",
                    str(video_path),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            return float(result.stdout.strip())
        except (subprocess.CalledProcessError, ValueError):
            return None

    def _find_source_video(self, analysis_dir: Path) -> Path:
        candidates = sorted(
            path
            for path in analysis_dir.iterdir()
            if path.is_file() and path.name.startswith("source.")
        )
        if not candidates:
            raise MediaPreparationError("yt-dlp did not produce a source video.")
        return candidates[0]

    def _run(self, command: list[str]) -> None:
        try:
            subprocess.run(
                command,
                check=True,
                capture_output=True,
                text=True,
            )
        except subprocess.CalledProcessError as exc:
            stderr = exc.stderr.strip() or exc.stdout.strip() or "command failed"
            raise MediaPreparationError(stderr) from exc


def build_media_artifact_pipeline_from_env(
    *,
    mode: str | None,
    artifact_root: str | None,
) -> MediaArtifactPipeline | None:
    root = Path(artifact_root or "/tmp/badminton-analysis-artifacts")
    selected_mode = mode or "mock"

    if selected_mode == "none":
        return None
    if selected_mode == "shell":
        return ShellMediaArtifactPipeline(root)
    return MockMediaArtifactPipeline(root)
