#!/usr/bin/env python3
"""端到端测试：抖音链接 -> 下载视频 -> 提取音频 -> Whisper转文字."""

import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 1. 检查依赖
print("[*] 检查依赖...")
try:
    from faster_whisper import WhisperModel
    print("    [OK] faster-whisper")
except ImportError:
    print("    [X] faster-whisper 未安装，运行: pip install faster-whisper")
    sys.exit(1)

try:
    import httpx
    print("    [OK] httpx")
except ImportError:
    print("    [X] httpx 未安装")
    sys.exit(1)

# 2. 获取链接
url = input("\n粘贴抖音链接: ").strip()
if not url:
    print("[X] 链接不能为空")
    sys.exit(1)

print(f"\n[*] 目标: {url[:60]}...")

# 3. 解析链接
print("\n[1/4] 解析抖音页面...")
from app.services.video_parsing_service import parse_video_link, _download_douyin_media, _extract_audio_for_asr

try:
    parsed = parse_video_link(url)
    print(f"    [OK] 标题: {parsed.title[:60]}")
    print(f"    [OK] 账号: {parsed.account_name or '未知'}")
except Exception as exc:
    print(f"    [X] 解析失败: {exc}")
    sys.exit(1)

# 4. 下载视频（需要media_url）
print("\n[2/4] 下载视频...")
# 注意：抖音解析出来的original_script是页面文案，不是视频音频转写
# 如果要真正的ASR，需要下载视频文件
# 但抖音链接解析通常只能拿到标题/文案，拿不到视频直链
# 这里我们提示用户

print("    [!] 抖音反爬严格，自动下载视频直链经常失败")
print("    [!] 页面文案已获取（标题+描述），但这不等于口播内容")
print(f"\n    页面文案预览:\n    {parsed.original_script[:300]}...")

# 尝试下载（如果解析到了media_url）
if parsed.source_url:
    print("\n[3/4] 尝试下载视频...")
    try:
        from app.core.config import get_settings
        settings = get_settings()
        downloaded = _download_douyin_media(parsed.source_url)
        print(f"    [OK] 下载完成: {downloaded.path}")
        print(f"    [OK] 大小: {len(downloaded.content) / 1024 / 1024:.1f} MB")

        # 提取音频
        print("\n[4/4] 提取音频并转写...")
        audio_path = _extract_audio_for_asr(downloaded.path)
        print(f"    [OK] 音频提取完成: {audio_path}")

        # Whisper转写
        print("    [*] 加载Whisper模型 (medium)...")
        model = WhisperModel("medium", device="cuda", compute_type="float16")
        print("    [OK] 模型加载完成")

        print("    [*] 开始转写...")
        segments, info = model.transcribe(audio_path, language="zh", vad_filter=True)

        print(f"\n{'='*60}")
        print(f"转写结果 (语言: {info.language}, 概率: {info.language_probability:.2%})")
        print(f"{'='*60}\n")

        full_text = []
        for seg in segments:
            print(f"[{seg.start:.1f}s - {seg.end:.1f}s] {seg.text}")
            full_text.append(seg.text)

        print(f"\n{'='*60}")
        print("完整文案:")
        print(f"{'='*60}")
        print("".join(full_text))

        # 清理临时文件
        os.remove(downloaded.path)
        os.remove(audio_path)

    except Exception as exc:
        print(f"    [X] 下载/转写失败: {exc}")
        print("    [!] 建议：把视频保存到本地，直接用本地文件测试")

else:
    print("    [X] 未能获取视频下载链接")
    print("    [!] 抖音反爬导致，请尝试:")
    print("        1. 用抖音APP分享 -> 复制链接")
    print("        2. 用网页版打开视频 -> 复制地址栏链接")
    print("        3. 如果都不行，把视频保存到本地再测")
