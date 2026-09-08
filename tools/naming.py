#!/usr/bin/env python3
"""name テーブル・メトリクス・ライセンス情報の整備。

書体名やデザイナー名を変えたい場合はこのファイルの定数を書き換える。
"""
from __future__ import annotations

import math

from fontTools.ttLib import TTFont

FAMILY = "Koshin Pop"
FAMILY_JA = "光信ポップ"
VERSION = "1.000"
DESIGNER = "Koshin Murakami"
DESIGNER_URL = "https://github.com/murakamikoshin"
VENDOR_ID = "KSHN"

COPYRIGHT = (
    "Copyright 2026 The Koshin Pop Project Authors "
    "(https://github.com/murakamikoshin/Koshin-Font). "
    "Based on Zen Maru Gothic, Copyright 2021 The Zen Maru Gothic Authors "
    "(https://github.com/googlefonts/zen-marugothic)."
)
LICENSE_DESC = (
    "This Font Software is licensed under the SIL Open Font License, Version 1.1. "
    "This license is available with a FAQ at https://openfontlicense.org"
)
LICENSE_URL = "https://openfontlicense.org"

DESCRIPTION_EN = (
    "A bouncy Japanese typeface. Every character gets its own leap, tilt and "
    "size, so text springs along the line. Made for headlines and logotypes."
)
DESCRIPTION_JA = (
    "文字ごとに跳ね方・傾き・大きさが変わる、弾ける日本語書体。"
    "見出しやロゴなど、元気さを出したい場面向け。"
)

# スタイル名 -> (usWeightClass, RIBBI ファミリー名の接尾辞, RIBBI サブファミリー)
#
# 4 スタイルしか持てない古いアプリでも全ウェイトが選べるように、
# Black は独立したファミリーとして登録しつつ、typographic family (16/17)
# で本来のファミリーに束ねている。
STYLES = {
    "Regular": {"weight": 400, "ribbi_suffix": "", "ribbi_style": "Regular", "ja": "レギュラー"},
    "Bold": {"weight": 700, "ribbi_suffix": "", "ribbi_style": "Bold", "ja": "ボールド"},
    "Black": {"weight": 900, "ribbi_suffix": " Black", "ribbi_style": "Regular", "ja": "ブラック"},
}

WINDOWS_EN = (3, 1, 0x0409)
WINDOWS_JA = (3, 1, 0x0411)
MAC_EN = (1, 0, 0)


def _set(name_table, name_id: int, value: str, *, japanese: str | None = None) -> None:
    """英語名（と必要なら日本語名）を name テーブルに登録する。

    Mac プラットフォームのレコードは MacRoman でしか符号化できないので、
    ASCII に収まる文字列のときだけ書き込む。
    """
    name_table.setName(value, name_id, *WINDOWS_EN)
    if value.isascii():
        name_table.setName(value, name_id, *MAC_EN)
    if japanese:
        name_table.setName(japanese, name_id, *WINDOWS_JA)


def apply_names(font: TTFont, style: str) -> None:
    """name テーブルを Koshin Pop のものに置き換える。"""
    spec = STYLES[style]
    ribbi_family = FAMILY + spec["ribbi_suffix"]
    ribbi_style = spec["ribbi_style"]
    postscript = f"{FAMILY.replace(' ', '')}-{style}"

    name_table = font["name"]
    name_table.names = []  # 元フォントの名前は残さず作り直す

    _set(name_table, 0, COPYRIGHT)
    _set(name_table, 1, ribbi_family, japanese=FAMILY_JA + spec["ribbi_suffix"])
    _set(name_table, 2, ribbi_style)
    _set(name_table, 3, f"{VERSION};{VENDOR_ID};{postscript}")
    _set(name_table, 4, f"{ribbi_family} {ribbi_style}",
         japanese=f"{FAMILY_JA}{spec['ribbi_suffix']} {ribbi_style}")
    _set(name_table, 5, f"Version {VERSION}")
    _set(name_table, 6, postscript)
    _set(name_table, 8, DESIGNER)
    _set(name_table, 9, DESIGNER)
    _set(name_table, 10, DESCRIPTION_EN, japanese=DESCRIPTION_JA)
    _set(name_table, 11, DESIGNER_URL)
    _set(name_table, 12, DESIGNER_URL)
    _set(name_table, 13, LICENSE_DESC)
    _set(name_table, 14, LICENSE_URL)
    # typographic family / subfamily。Black を同一ファミリーに束ねる。
    _set(name_table, 16, FAMILY, japanese=FAMILY_JA)
    _set(name_table, 17, style, japanese=spec["ja"])


def apply_metadata(font: TTFont, style: str) -> None:
    """OS/2・head・post の各種フラグを整える。"""
    spec = STYLES[style]
    os2 = font["OS/2"]
    head = font["head"]

    os2.achVendID = VENDOR_ID
    os2.usWeightClass = spec["weight"]
    os2.fsType = 0  # 埋め込み自由（OFL に合わせる）

    is_bold = style == "Bold"
    # fsSelection: bit0 italic / bit5 bold / bit6 regular / bit7 useTypoMetrics
    fs = os2.fsSelection & ~(1 << 0 | 1 << 5 | 1 << 6)
    fs |= (1 << 5) if is_bold else (1 << 6)
    fs |= 1 << 7
    os2.fsSelection = fs

    head.macStyle = (head.macStyle & ~0b11) | (0b1 if is_bold else 0)

    head.fontRevision = float(VERSION)
    font["post"].italicAngle = 0.0
    font["post"].isFixedPitch = 0


def retune_vertical_metrics(font: TTFont, headroom: int = 24) -> tuple[int, int]:
    """跳ね上げで字面がはみ出すぶん、行の上下に余裕を持たせる。

    Windows は usWinAscent/usWinDescent の外側を描画時にクリップすることが
    あるので、実際の輪郭の最大・最小から計算し直す。
    """
    glyf = font["glyf"]
    top, bottom = 0, 0
    for name in font.getGlyphOrder():
        g = glyf[name]
        if g.numberOfContours == 0:
            continue
        g.recalcBounds(glyf)
        top = max(top, g.yMax)
        bottom = min(bottom, g.yMin)

    ascent = int(math.ceil(top)) + headroom
    descent = int(math.ceil(-bottom)) + headroom

    os2, hhea = font["OS/2"], font["hhea"]
    os2.usWinAscent = ascent
    os2.usWinDescent = descent
    # 行送りの基準となる typo メトリクスは仮想ボディ（em）を基準に据え、
    # 跳ねたぶんは lineGap で吸収する。行間が詰まりすぎるのを防ぐため。
    os2.sTypoAscender = 880
    os2.sTypoDescender = -120
    os2.sTypoLineGap = max(0, (ascent + descent) - 1000)
    hhea.ascent, hhea.descent, hhea.lineGap = ascent, -descent, 0
    return ascent, descent
