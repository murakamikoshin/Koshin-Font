#!/usr/bin/env python3
"""Koshin Pop の中核となる「弾ける」変形エンジン。

全グリフに対して、その文字ごとに決まった量の

  * 跳ね上げ  (baseline からの上下オフセット)
  * 傾き      (視覚中心まわりの回転)
  * ポップ    (拡大縮小。跳ね上がったものほど大きく＝手前に飛び出して見える)

を与える。乱数はグリフ名から決定的に導出するので、同じ文字は常に同じ
表情になり、ビルドを繰り返しても結果は完全に再現する。

字種ごとに振れ幅を変えているのが設計上の要点。日本語の組版ではリズムを
作るのは仮名なので仮名を大きく振り、可読性の負荷が高い漢字は控えめに、
単独で並ぶことが多い欧文・数字はいちばん大きく振っている。
"""
from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass

from fontTools.misc.transform import Transform
from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont

# アウトラインを書き換えると無効になるテーブル群。
STALE_TABLES = ("fpgm", "prep", "cvt ", "hdmx", "LTSH", "VDMX", "gasp")


def decompose_composites(font: TTFont) -> int:
    """合成グリフをすべて単独の輪郭に展開する。

    変形をかける前に必ず通しておく必要がある。合成グリフのまま変形すると、
    参照先の基本グリフにかかった変形と二重にかかってしまうため。
    """
    glyf = font["glyf"]
    glyph_set = font.getGlyphSet()
    decomposed = 0
    for name in font.getGlyphOrder():
        glyph = glyf[name]
        if not glyph.isComposite():
            continue
        recording = DecomposingRecordingPen(glyph_set)
        glyph_set[name].draw(recording)
        pen = TTGlyphPen(None)
        recording.replay(pen)
        new_glyph = pen.glyph()
        new_glyph.recalcBounds(glyf)
        glyf[name] = new_glyph
        decomposed += 1
    return decomposed


@dataclass(frozen=True)
class Motion:
    """ある字種に与える動きの振れ幅（1000 upem 基準 / 度 / 倍率）。"""

    rise: float       # 跳ね上げの振れ幅 (±)
    tilt: float       # 傾きの振れ幅 (±, 度)
    pop: float        # 拡大縮小の振れ幅 (±, 1.0 からの差)
    squash: float     # スクワッシュ＆ストレッチの強さ (±, 縦横比の偏り)
    lift_bias: float = 0.0  # 跳ね上げの中心をずらす量（正で全体が浮く）


# 字種ごとの設定。build.py から差し替えられる。
#
# 欧文・数字がいちばん大きく振れ、仮名がそれに次ぎ、漢字は画数が多く
# 可読性への負荷が大きいので控えめにしてある。ただし漢字だけ動きが
# 止まって見えないよう、仮名の 6 割程度の振れは残している。
DEFAULT_MOTION = {
    "latin": Motion(rise=52, tilt=7.0, pop=0.090, squash=0.055),
    "digit": Motion(rise=52, tilt=7.0, pop=0.090, squash=0.055),
    "punct": Motion(rise=40, tilt=8.0, pop=0.080, squash=0.050),
    "kana": Motion(rise=46, tilt=6.0, pop=0.080, squash=0.050),
    "kanji": Motion(rise=30, tilt=3.2, pop=0.050, squash=0.030),
    "other": Motion(rise=22, tilt=2.4, pop=0.034, squash=0.022),
}

# 跳ね上げと拡大率をどれだけ連動させるか。1.0 で完全連動し、
# 上に跳ねた文字ほど大きく＝手前に飛び出して見える。
POP_CORRELATION = 0.75

KANA_RANGES = ((0x3041, 0x30FF), (0x31F0, 0x31FF), (0xFF66, 0xFF9F))
KANJI_RANGES = ((0x3400, 0x4DBF), (0x4E00, 0x9FFF), (0xF900, 0xFAFF), (0x20000, 0x2FFFF))
PUNCT_RANGES = ((0x0021, 0x002F), (0x003A, 0x0040), (0x005B, 0x0060), (0x007B, 0x007E),
                (0x2000, 0x206F), (0x3000, 0x303F), (0xFF01, 0xFF20), (0xFF3B, 0xFF40),
                (0xFF5B, 0xFF65))


def _in(cp: int, ranges) -> bool:
    return any(lo <= cp <= hi for lo, hi in ranges)


def categorize(codepoint: int | None) -> str:
    """コードポイントから字種を判定する。"""
    if codepoint is None:
        return "other"
    if 0x30 <= codepoint <= 0x39 or _in(codepoint, ((0xFF10, 0xFF19),)):
        return "digit"
    if 0x41 <= codepoint <= 0x5A or 0x61 <= codepoint <= 0x7A or 0x00C0 <= codepoint <= 0x024F:
        return "latin"
    if _in(codepoint, KANA_RANGES):
        return "kana"
    if _in(codepoint, KANJI_RANGES):
        return "kanji"
    if _in(codepoint, PUNCT_RANGES):
        return "punct"
    return "other"


def _unit(key: str, salt: str) -> float:
    """グリフ名と用途から -1.0〜1.0 の決定的な値を作る。"""
    digest = hashlib.sha256(f"koshin-pop/{salt}/{key}".encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big") / 2**63 - 1.0


def motion_for(glyph_name: str, category: str, table: dict[str, Motion],
               correlation: float = POP_CORRELATION) -> tuple[float, float, float, float]:
    """(跳ね上げ量, 傾き角, 横倍率, 縦倍率) を返す。"""
    m = table.get(category, table["other"])

    rise_u = _unit(glyph_name, "rise")
    tilt_u = _unit(glyph_name, "tilt")
    pop_u = _unit(glyph_name, "pop")

    dy = rise_u * m.rise + m.lift_bias
    tilt = tilt_u * m.tilt

    # 拡大率は「跳ね上げに連動する分」と「独自に振れる分」の合成。
    pop_mix = correlation * rise_u + (1.0 - correlation) * pop_u
    scale = 1.0 + pop_mix * m.pop

    # スクワッシュ＆ストレッチ。跳ね上がった字は縦に伸び、沈んだ字は
    # 横に潰れる。弾むボールの挙動そのもので、これが入るとただの
    # ランダムな上下動が「弾んでいる」動きに見えるようになる。
    sx = scale * (1.0 - m.squash * rise_u)
    sy = scale * (1.0 + m.squash * rise_u)
    return dy, tilt, sx, sy


def _pivot(bounds, advance: int) -> tuple[float, float]:
    """回転・拡大の中心。水平は字送りの中央、垂直は字面の中央にとる。"""
    x = advance / 2.0
    if bounds is None:
        return x, 250.0
    _, y_min, _, y_max = bounds
    return x, (y_min + y_max) / 2.0


def apply_bounce(font: TTFont, motion_table: dict[str, Motion] | None = None,
                 correlation: float = POP_CORRELATION,
                 verbose: bool = False) -> dict[str, int]:
    """フォント全体に弾ける変形をかける。処理したグリフ数を字種別に返す。"""
    table = motion_table or DEFAULT_MOTION
    decompose_composites(font)
    glyf = font["glyf"]
    hmtx = font["hmtx"]
    vmtx = font.get("vmtx")
    glyph_set = font.getGlyphSet()

    # 縦組み用の原点（vertOriginY）は変形前の値を覚えておき、あとで
    # 新しい字面から tsb を計算し直す。こうしないと縦書きのときだけ
    # 跳ね上げが打ち消されてしまう。
    vertical_origins: dict[str, int] = {}
    if vmtx is not None:
        for name in font.getGlyphOrder():
            g = glyf[name]
            if g.numberOfContours == 0:
                continue
            g.recalcBounds(glyf)
            vertical_origins[name] = g.yMax + vmtx[name][1]

    # グリフ名 -> 代表コードポイント（字種判定用）
    cmap = font.getBestCmap()
    reverse: dict[str, int] = {}
    for cp, name in cmap.items():
        reverse.setdefault(name, cp)

    def category_of(glyph_name: str) -> str:
        cp = reverse.get(glyph_name)
        if cp is None and "." in glyph_name:
            # "a.pop1" のような派生グリフは元の文字の字種を引き継ぐ
            cp = reverse.get(glyph_name.split(".", 1)[0])
        return categorize(cp)

    counts: dict[str, int] = {}
    for name in font.getGlyphOrder():
        glyph = glyf[name]
        if glyph.numberOfContours == 0:
            continue  # 空白グリフは動かさない

        category = category_of(name)
        counts[category] = counts.get(category, 0) + 1

        dy, tilt, sx, sy = motion_for(name, category, table, correlation)
        advance = hmtx[name][0]
        glyph.recalcBounds(glyf)
        px, py = _pivot((glyph.xMin, glyph.yMin, glyph.xMax, glyph.yMax), advance)

        transform = (
            Transform()
            .translate(0, dy)
            .translate(px, py)
            .rotate(math.radians(tilt))
            .scale(sx, sy)
            .translate(-px, -py)
        )

        recording = DecomposingRecordingPen(glyph_set)
        glyph_set[name].draw(recording)

        pen = TTGlyphPen(None)
        recording.replay(TransformPen(pen, transform))
        new_glyph = pen.glyph()
        new_glyph.recalcBounds(glyf)
        glyf[name] = new_glyph

        # 字面が動いたので、サイドベアリングを新しい輪郭に合わせ直す。
        hmtx[name] = (advance, new_glyph.xMin)
        if vmtx is not None and name in vertical_origins:
            vmtx[name] = (vmtx[name][0], vertical_origins[name] - new_glyph.yMax)

    for tag in STALE_TABLES:
        if tag in font:
            del font[tag]

    if verbose:
        for key in sorted(counts):
            print(f"    {key:<6} {counts[key]:>5} グリフ")
    return counts
