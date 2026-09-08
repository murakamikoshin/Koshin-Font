#!/usr/bin/env python3
"""ビルドしたフォントを PNG に描画して目視確認するための見本作成ツール。

使い方: python3 tools/proof.py build/KoshinPop-Bold.ttf docs/proof-bold.png
"""
from __future__ import annotations

import sys

from PIL import Image, ImageDraw, ImageFont

BG = (255, 252, 245)
INK = (32, 28, 26)
ACCENT = (226, 88, 62)

LINES = [
    (58, ACCENT, "恒紳ポップ Koshin Pop"),
    (34, INK, "あいうえお かきくけこ さしすせそ たちつてと"),
    (34, INK, "アイウエオ ガギグゲゴ パピプペポ ヴッャュョ"),
    (34, INK, "弾ける感じの日本語書体を作りました。"),
    (34, INK, "春夏秋冬 月火水木金土日 東京都渋谷区神南"),
    (34, INK, "ABCDEFGHIJKLM NOPQRSTUVWXYZ"),
    (34, INK, "abcdefghijklm nopqrstuvwxyz"),
    (34, INK, "0123456789 !?&@#%（），。「」…"),
    (24, INK, "吾輩は猫である。名前はまだ無い。どこで生れたか"),
    (24, INK, "とんと見当がつかぬ。何でも薄暗いじめじめした所で"),
    (18, INK, "The quick brown fox jumps over the lazy dog. 1234567890"),
]


def render(font_path: str, out_path: str, width: int = 1400) -> None:
    pad = 56
    heights = [int(size * 1.85) for size, _, _ in LINES]
    height = pad * 2 + sum(heights)

    img = Image.new("RGB", (width, height), BG)
    draw = ImageDraw.Draw(img)

    y = pad
    for (size, color, text), line_h in zip(LINES, heights):
        font = ImageFont.truetype(font_path, size)
        draw.text((pad, y + line_h * 0.15), text, font=font, fill=color)
        y += line_h

    img.save(out_path)
    print(f"{out_path}  ({width}x{height})")


if __name__ == "__main__":
    render(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "proof.png")
