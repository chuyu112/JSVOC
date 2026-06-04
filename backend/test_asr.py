"""Test script: download Douyin video -> extract audio -> transcribe with Whisper."""

import sys

# Check faster-whisper installed
try:
    from faster_whisper import WhisperModel
    print("[OK] faster-whisper installed")
except ImportError:
    print("[X] faster-whisper not installed")
    print("    Run: pip install faster-whisper")
    sys.exit(1)

# Check ffmpeg
try:
    import subprocess
    subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
    print("[OK] ffmpeg installed")
except Exception:
    print("[X] ffmpeg not found in PATH")
    print("    Download: https://ffmpeg.org/download.html")
    sys.exit(1)

# Test URL
URL = "https://v.douyin.com/69hzCvXx1aM/"

print(f"\n[*] Testing Douyin ASR pipeline")
print(f"    URL: {URL}")

# Step 1: Parse video link
print("\n[1/4] Parsing Douyin link...")
from app.services.video_parsing_service import parse_video_link
try:
    result = parse_video_link(URL)
    print(f"    Title: {result.title[:60]}...")
    print(f"    Script preview: {result.original_script[:100]}...")
except Exception as exc:
    print(f"    [X] Parse failed: {exc}")
    print("    Tip: Try manual input if auto-parse fails")
    sys.exit(1)

# Step 2: Download media (if media_url available)
# Note: This requires actual download, skip if no media_url

# Step 3: Transcribe with Whisper
print("\n[2/4] Loading Whisper model (first run downloads ~3GB)...")
model = WhisperModel("medium", device="cuda", compute_type="float16")
print("    [OK] Model loaded")

print("\n[3/4] Note: Full test requires downloading the video file first.")
print("    The parse_video_link function returned the page title/desc,")
    print("    but the actual video download + ASR needs the media URL.")

print("\n[4/4] Pipeline check complete.")
print("    To do full ASR test:")
print("    1. Open frontend -> AI爆款仿写")
print("    2. Paste the Douyin link")
print("    3. Click '解析链接' then '转写'")
