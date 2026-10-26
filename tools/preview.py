"""Workshop preview: assets/preview.png scaled down to the launcher's 512x512.

Written by tools/build.py next to the pack as dist/agent_cooldowns.png. Steam rejects previews of 1 MB or more.
"""
from PIL import Image

from tools.paths import ROOT

SOURCE = ROOT / "assets" / "preview.png"
SIZE = 512


def make_preview():
    return Image.open(SOURCE).convert("RGB").resize((SIZE, SIZE), Image.LANCZOS)


def save_preview(img, path):
    img.save(path, "PNG", optimize=True)
