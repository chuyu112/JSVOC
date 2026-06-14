"""FFmpeg video composition service for digital human output."""

import logging
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class VideoComposeService:
    """Compose final video with subtitles and BGM using FFmpeg."""

    def compose(
        self,
        video_path: str,
        subtitle_text: str,
        output_path: str,
        bgm_path: str | None = None,
        resolution: str = "1080p",
    ) -> str:
        """Compose final video.

        Args:
            video_path: Path to raw digital human video (from HeyGem).
            subtitle_text: Script text for subtitles.
            output_path: Output file path.
            bgm_path: Optional background music.
            resolution: Output resolution.

        Returns:
            Path to the final composed video.
        """
        if not Path(video_path).exists():
            raise FileNotFoundError(f"Video not found: {video_path}")

        # Build FFmpeg command
        cmd = [
            "ffmpeg",
            "-y",
            "-i", video_path,
        ]

        # Add BGM if provided
        if bgm_path and Path(bgm_path).exists():
            cmd.extend(["-i", bgm_path])
            # Mix audio: video audio at full volume, BGM at 30%
            cmd.extend([
                "-filter_complex",
                "[0:a][1:a]amix=inputs=2:duration=first:weights=1 0.3[aout]",
                "-map", "0:v",
                "-map", "[aout]",
            ])

        # Add subtitles (burn-in)
        if subtitle_text:
            # Create ASS subtitle file
            ass_path = self._create_ass_subtitle(video_path, subtitle_text)
            cmd.extend([
                "-vf", f"ass={ass_path}",
            ])

        # Resolution
        scale_map = {"720p": "1280:720", "1080p": "1920:1080", "4k": "3840:2160"}
        if resolution in scale_map:
            # Insert scale before subtitle if not already filtered
            pass  # Simplified for now

        cmd.extend([
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "23",
            "-c:a", "aac",
            "-b:a", "192k",
            output_path,
        ])

        try:
            subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=300)
            logger.info("Video composed: %s", output_path)
            return output_path
        except subprocess.CalledProcessError as exc:
            logger.error("FFmpeg failed: %s", exc.stderr.decode("utf-8", errors="ignore")[:500])
            raise RuntimeError(f"视频合成失败: {exc}") from exc

    def _create_ass_subtitle(self, video_path: str, text: str) -> str:
        """Create a simple ASS subtitle file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".ass", delete=False, encoding="utf-8") as f:
            f.write("[Script Info]\n")
            f.write("Title: JSVOC Subtitle\n")
            f.write("ScriptType: v4.00+\n\n")
            f.write("[V4+ Styles]\n")
            f.write("Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n")
            f.write("Style: Default,Arial,24,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,10,1\n\n")
            f.write("[Events]\n")
            f.write("Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")
            # Simple: show full text for 10 seconds
            f.write(f"Dialogue: 0,0:00:00.00,0:00:10.00,Default,,0,0,0,,{text}\n")
            return f.name
