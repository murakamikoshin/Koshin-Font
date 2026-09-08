#!/usr/bin/env python3
"""ベースフォントの欧文グリフを、latin.py で設計したオリジナル字形に差し替える。

字幅と字面の左右位置はベースフォントの値をそのまま使う。仮名・漢字との
間隔設計を引き継げるうえ、アクセント付き文字（合成グリフ）の位置合わせも
崩れない。合成グリフを展開する前に呼ぶこと。
"""
from __future__ import annotations

from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont

import latin
import strokes

# 各ウェイトの線の太さ。ベースフォントの I の字面幅（＝縦線の太さ）に
# 合わせてあり、仮名・漢字と並べたときの黒みがそろう。
STEM_BY_STYLE = {"Regular": 64, "Bold": 118, "Black": 134}


def swap_latin(font: TTFont, style: str,
               proportions: latin.Proportions | None = None) -> list[str]:
    """差し替えたグリフ名の一覧を返す。"""
    stem = STEM_BY_STYLE[style]
    props = proportions or latin.Proportions()

    glyf = font["glyf"]
    cmap = font.getBestCmap()
    glyph_set = font.getGlyphSet()

    replaced: list[str] = []
    for char, design in latin.DESIGNS.items():
        codepoint = ord(char)
        name = cmap.get(codepoint)
        if name is None:
            continue

        # 元グリフの字面の左右端を、そのまま新しい字形の枠として使う。
        bounds_pen = BoundsPen(glyph_set)
        glyph_set[name].draw(bounds_pen)
        if bounds_pen.bounds is None:
            continue
        x_min, _, x_max, _ = bounds_pen.bounds

        # i l I のように字面幅が線幅ぶんしかない字では x0 と x1 が一致する。
        box = latin.Box(x0=x_min + stem / 2.0,
                        x1=max(x_max - stem / 2.0, x_min + stem / 2.0),
                        stem=stem, p=props)

        pen = TTGlyphPen(None)
        strokes.draw_contours(design(box), pen)
        new_glyph = pen.glyph()
        new_glyph.recalcBounds(glyf)
        glyf[name] = new_glyph
        replaced.append(name)

    return replaced
