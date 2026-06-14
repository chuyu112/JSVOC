#!/usr/bin/env python3
"""一键测试：抖音链接 -> 视频 -> 音频 -> 文字"""

import os
import sys
import tempfile

# 检查依赖
try:
    from faster_whisper import WhisperModel
except ImportError:
    print("[X] faster-whisper 未安装")
    print("    运行: pip install faster-whisper")
    sys.exit(1)

try:
    import httpx
except ImportError:
    print("[X] httpx 未安装")
    sys.exit(1)

# 抖音链接（用户可以改这里）
DOUYIN_URL = input("粘贴抖音链接: ").strip() or "https://v.douyin.com/2xmhkbJxZdk/"

print(f"\n[*] 目标: {DOUYIN_URL}")

# Step 1: 解析链接获取标题和文案
print("\n[1/3] 解析抖音页面...")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app.services.video_parsing_service import parse_video_link

try:
    result = parse_video_link(DOUYIN_URL)
    print(f"    ✅ 标题: {result.title[:80]}")
    print(f"    ✅ 页面文案: {result.original_script[:200]}...")
except Exception as exc:
    print(f"    ⚠️  解析失败: {exc}")
    print("    继续尝试直接下载...")

# Step 2: 下载视频
print("\n[2/3] 下载视频...")
print("    (此步骤需要视频直链，当前通过页面解析可能获取不到)")
print("    如果你需要完整 ASR 测试，请:")
print("    1. 把视频保存到本地")
print("    2. 用下面的代码转写")

# Step 3: 加载模型
print("\n[3/3] 加载 Whisper 模型...")
print("    首次运行会下载模型 (~1.5GB for medium)")
model_size = "medium"  # 可改: tiny/base/small/medium/large-v3
device = "cuda" if os.system("nvidia-smi >/dev/null 2>&1") == 0 else "cpu"
compute = "float16" if device == "cuda" else "int8"

print(f"    配置: size={model_size}, device={device}, compute={compute}")
model = WhisperModel(model_size, device=device, compute_type=compute)
print("    ✅ 模型加载完成")

print("\n" + "="*50)
print("准备就绪！")
print("="*50)
print("\n要转写本地视频，运行:")
print('''
from faster_whisper import WhisperModel
model = WhisperModel("medium", device="cuda", compute_type="float16")
segments, info = model.transcribe("your_video.mp4", language="zh")
for seg in segments:
    print(f"[{seg.start:.1f}s - {seg.end:.1f}s] {seg.text}")
''')
