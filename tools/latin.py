#!/usr/bin/env python3
"""Koshin Pop のオリジナル欧文（A-Z / a-z / 0-9）の設計。

丸ゴシックの仮名・漢字に合うように、単線・ジオメトリックな骨格に丸い
線端を付けた書体として設計している。a と g は 1 階建て（Futura 型）に
して、幾何学的でポップな性格をはっきり出した。

字幅と字面の左右位置はベースフォントの欧文に合わせてある。仮名・漢字と
の間隔設計をそのまま引き継げるうえ、アクセント付きラテン文字（合成
グリフ）の位置もずれない。縦方向の比率だけは独自に決めていて、
ベースより x ハイトをわずかに大きく取り、丸みを強調している。
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import strokes
from strokes import arc, dot, line, ring

D = math.radians


@dataclass(frozen=True)
class Proportions:
    """縦方向の基準線。全ウェイト共通。"""

    cap: float = 700.0        # 大文字の高さ
    xheight: float = 500.0    # 小文字の高さ
    ascender: float = 722.0   # b d f h k l の高さ
    descender: float = -212.0 # g j p q y の深さ
    figure: float = 700.0     # 数字の高さ
    overshoot: float = 14.0   # 丸い字形が基準線を超える量


@dataclass(frozen=True)
class Box:
    """1 グリフ分の描画枠。骨格線の可動範囲を表す。"""

    x0: float   # 骨格線の左端（字面の左端 + 線幅/2）
    x1: float   # 骨格線の右端
    stem: float
    p: Proportions

    @property
    def w(self) -> float:
        return self.x1 - self.x0

    @property
    def xm(self) -> float:
        return (self.x0 + self.x1) / 2.0

    def round_ry(self, height: float) -> float:
        """丸い字形の縦半径。上下のオーバーシュートを含めた値。"""
        return (height + 2 * self.p.overshoot - self.stem) / 2.0


# --------------------------------------------------------------------------
# 大文字
# --------------------------------------------------------------------------

def _A(b: Box):
    c = b.p.cap
    bar = c * 0.27
    tx = b.xm
    left_at_bar = b.x0 + (tx - b.x0) * (bar / c)
    right_at_bar = b.x1 - (b.x1 - tx) * (bar / c)
    return [line((b.x0, 0), (tx, c), b.stem),
            line((tx, c), (b.x1, 0), b.stem),
            line((left_at_bar, bar), (right_at_bar, bar), b.stem)]


def _B(b: Box):
    c, mid = b.p.cap, b.p.cap * 0.525
    return [line((b.x0, 0), (b.x0, c), b.stem),
            arc((b.x0, (c + mid) / 2), (b.x1 - b.x0) * 0.86, (c - mid) / 2,
                D(90), D(-90), b.stem, cap0="butt", cap1="butt"),
            arc((b.x0, mid / 2), b.x1 - b.x0, mid / 2,
                D(90), D(-90), b.stem, cap0="butt", cap1="butt")]


def _C(b: Box):
    return [arc((b.xm, b.p.cap / 2), b.w / 2, b.round_ry(b.p.cap),
                D(55), D(305), b.stem)]


def _D(b: Box):
    c = b.p.cap
    return [line((b.x0, 0), (b.x0, c), b.stem),
            arc((b.x0, c / 2), b.x1 - b.x0, c / 2, D(90), D(-90), b.stem,
                cap0="butt", cap1="butt")]


def _E(b: Box):
    c = b.p.cap
    return [line((b.x0, 0), (b.x0, c), b.stem),
            line((b.x0, c), (b.x1, c), b.stem),
            line((b.x0, c * 0.5), (b.x1 - b.w * 0.10, c * 0.5), b.stem),
            line((b.x0, 0), (b.x1, 0), b.stem)]


def _F(b: Box):
    c = b.p.cap
    return [line((b.x0, 0), (b.x0, c), b.stem),
            line((b.x0, c), (b.x1, c), b.stem),
            line((b.x0, c * 0.5), (b.x1 - b.w * 0.06, c * 0.5), b.stem)]


def _G(b: Box):
    c = b.p.cap
    rx, ry = b.w / 2, b.round_ry(c)
    return [arc((b.xm, c / 2), rx, ry, D(55), D(360), b.stem),
            line((b.xm + rx * 0.12, c / 2), (b.x1, c / 2), b.stem)]


def _H(b: Box):
    c = b.p.cap
    return [line((b.x0, 0), (b.x0, c), b.stem),
            line((b.x1, 0), (b.x1, c), b.stem),
            line((b.x0, c * 0.5), (b.x1, c * 0.5), b.stem)]


def _I(b: Box):
    return [line((b.xm, 0), (b.xm, b.p.cap), b.stem)]


def _J(b: Box):
    c = b.p.cap
    rx = b.w / 2
    ry = min(rx, c * 0.30)
    return [line((b.x1, c), (b.x1, ry), b.stem, cap1="butt"),
            arc((b.x1 - rx, ry), rx, ry, D(0), D(-180), b.stem, cap0="butt")]


def _K(b: Box):
    c = b.p.cap
    joint = (b.x0 + b.stem * 0.15, c * 0.40)
    return [line((b.x0, 0), (b.x0, c), b.stem),
            line(joint, (b.x1, c), b.stem),
            line(joint, (b.x1, 0), b.stem)]


def _L(b: Box):
    return [line((b.x0, 0), (b.x0, b.p.cap), b.stem),
            line((b.x0, 0), (b.x1, 0), b.stem)]


def _M(b: Box):
    c = b.p.cap
    return [line((b.x0, 0), (b.x0, c), b.stem),
            line((b.x1, 0), (b.x1, c), b.stem),
            line((b.x0, c), (b.xm, c * 0.20), b.stem),
            line((b.xm, c * 0.20), (b.x1, c), b.stem)]


def _N(b: Box):
    c = b.p.cap
    return [line((b.x0, 0), (b.x0, c), b.stem),
            line((b.x1, 0), (b.x1, c), b.stem),
            line((b.x0, c), (b.x1, 0), b.stem)]


def _O(b: Box):
    return ring((b.xm, b.p.cap / 2), b.w / 2, b.round_ry(b.p.cap), b.stem)


def _P(b: Box):
    c, mid = b.p.cap, b.p.cap * 0.46
    return [line((b.x0, 0), (b.x0, c), b.stem),
            arc((b.x0, (c + mid) / 2), b.x1 - b.x0, (c - mid) / 2,
                D(90), D(-90), b.stem, cap0="butt", cap1="butt")]


def _Q(b: Box):
    c = b.p.cap
    rx, ry = b.w / 2, b.round_ry(c)
    # 尻尾は輪の上（骨格線）から生やす。内側から始めるとカウンターを潰す。
    tail0 = (b.xm + rx * math.cos(D(-50)), c / 2 + ry * math.sin(D(-50)))
    tail1 = (b.xm + rx * 1.05, -b.p.overshoot - c * 0.09)
    return ring((b.xm, c / 2), rx, ry, b.stem) + [line(tail0, tail1, b.stem)]


def _R(b: Box):
    c, mid = b.p.cap, b.p.cap * 0.47
    return [line((b.x0, 0), (b.x0, c), b.stem),
            arc((b.x0, (c + mid) / 2), (b.x1 - b.x0) * 0.94, (c - mid) / 2,
                D(90), D(-90), b.stem, cap0="butt", cap1="butt"),
            line((b.x0 + b.stem * 0.15, mid), (b.x1, 0), b.stem)]


def _spine(b: Box, height: float, base: float = 0.0):
    """S / s の背骨。上下ふたつの円弧を接線が連続するようにつなぐ。

    骨格の縦方向を半分ずつに分け、上下それぞれに同じ半径の円弧を置くと
    継ぎ目で接線が水平にそろい、なめらかな S になる。
    """
    rx = b.w / 2
    half = (height + 2 * b.p.overshoot - b.stem) / 2.0  # 骨格の縦半径
    cy = base + height / 2.0
    ry = half / 2.0
    return [arc((b.xm, cy + ry), rx, ry, D(20), D(270), b.stem),
            arc((b.xm, cy - ry), rx, ry, D(90), D(-160), b.stem)]


def _S(b: Box):
    return _spine(b, b.p.cap)


def _T(b: Box):
    c = b.p.cap
    return [line((b.x0, c), (b.x1, c), b.stem),
            line((b.xm, 0), (b.xm, c), b.stem)]


def _U(b: Box):
    c = b.p.cap
    rx = b.w / 2
    ry = min(rx, c * 0.38)
    return [line((b.x0, c), (b.x0, ry), b.stem, cap1="butt"),
            line((b.x1, c), (b.x1, ry), b.stem, cap1="butt"),
            arc((b.xm, ry), rx, ry, D(180), D(360), b.stem, cap0="butt", cap1="butt")]


def _V(b: Box):
    c = b.p.cap
    return [line((b.x0, c), (b.xm, 0), b.stem),
            line((b.xm, 0), (b.x1, c), b.stem)]


def _W(b: Box):
    c = b.p.cap
    a = b.x0 + b.w * 0.27
    d = b.x1 - b.w * 0.27
    return [line((b.x0, c), (a, 0), b.stem),
            line((a, 0), (b.xm, c * 0.70), b.stem),
            line((b.xm, c * 0.70), (d, 0), b.stem),
            line((d, 0), (b.x1, c), b.stem)]


def _X(b: Box):
    c = b.p.cap
    return [line((b.x0, 0), (b.x1, c), b.stem),
            line((b.x1, 0), (b.x0, c), b.stem)]


def _Y(b: Box):
    c = b.p.cap
    joint = (b.xm, c * 0.46)
    return [line((b.x0, c), joint, b.stem),
            line((b.x1, c), joint, b.stem),
            line((b.xm, 0), joint, b.stem)]


def _Z(b: Box):
    c = b.p.cap
    return [line((b.x0, c), (b.x1, c), b.stem),
            line((b.x1, c), (b.x0, 0), b.stem),
            line((b.x0, 0), (b.x1, 0), b.stem)]


CAPITALS = {
    "A": _A, "B": _B, "C": _C, "D": _D, "E": _E, "F": _F, "G": _G, "H": _H,
    "I": _I, "J": _J, "K": _K, "L": _L, "M": _M, "N": _N, "O": _O, "P": _P,
    "Q": _Q, "R": _R, "S": _S, "T": _T, "U": _U, "V": _V, "W": _W, "X": _X,
    "Y": _Y, "Z": _Z,
}


# --------------------------------------------------------------------------
# 小文字
#
# a と g を 1 階建てにしているのがこの書体の性格を決めている。丸ゴシック
# の仮名と並べたときに、幾何学的な明るさが揃う。
# --------------------------------------------------------------------------

def _a(b: Box):
    x = b.p.xheight
    return ring((b.xm, x / 2), b.w / 2, b.round_ry(x), b.stem) + [
        line((b.x1, 0), (b.x1, x / 2), b.stem, cap1="butt")]


def _b(b: Box):
    x = b.p.xheight
    return [line((b.x0, 0), (b.x0, b.p.ascender), b.stem)] + \
        ring((b.xm, x / 2), b.w / 2, b.round_ry(x), b.stem)


def _c(b: Box):
    x = b.p.xheight
    return [arc((b.xm, x / 2), b.w / 2, b.round_ry(x), D(50), D(310), b.stem)]


def _d(b: Box):
    x = b.p.xheight
    return [line((b.x1, 0), (b.x1, b.p.ascender), b.stem)] + \
        ring((b.xm, x / 2), b.w / 2, b.round_ry(x), b.stem)


def _e(b: Box):
    x = b.p.xheight
    rx, ry = b.w / 2, b.round_ry(x)
    cy = x / 2
    bar_y = cy + ry * 0.06
    a0 = math.asin(max(-1.0, min(1.0, (bar_y - cy) / ry)))
    return [line((b.xm - rx, bar_y), (b.xm + rx * math.cos(a0), bar_y), b.stem,
                 cap1="butt"),
            arc((b.xm, cy), rx, ry, a0, D(310), b.stem, cap0="butt")]


def _f(b: Box):
    x, asc = b.p.xheight, b.p.ascender
    stem_x = b.x0 + b.w * 0.34
    r = b.x1 - stem_x
    return [line((stem_x, 0), (stem_x, asc - r), b.stem, cap1="butt"),
            arc((stem_x + r, asc - r), r, r, D(180), D(90), b.stem, cap0="butt"),
            line((b.x0, x), (b.x1, x), b.stem)]


def _g(b: Box):
    x, desc = b.p.xheight, b.p.descender
    rx = b.w / 2
    hook_rx = b.w * 0.48
    hook_ry = min(hook_rx, 100.0)
    return ring((b.xm, x / 2), rx, b.round_ry(x), b.stem) + [
        line((b.x1, x / 2), (b.x1, desc + hook_ry), b.stem, cap0="butt", cap1="butt"),
        arc((b.x1 - hook_rx, desc + hook_ry), hook_rx, hook_ry,
            D(0), D(-155), b.stem, cap0="butt")]


def _arch(b: Box, height: float, rx: float, cx: float):
    """n m h r の肩。左の縦線の上から右へ回り込む半円。"""
    ry = min(rx, height * 0.46)
    return arc((cx, height - ry), rx, ry, D(180), D(0), b.stem,
               cap0="butt", cap1="butt"), height - ry


def _h(b: Box):
    x = b.p.xheight
    shoulder, joint_y = _arch(b, x, b.w / 2, b.xm)
    return [line((b.x0, 0), (b.x0, b.p.ascender), b.stem), shoulder,
            line((b.x1, 0), (b.x1, joint_y), b.stem, cap1="butt")]


def _i(b: Box):
    x = b.p.xheight
    r = b.stem * 0.60
    return [line((b.xm, 0), (b.xm, x), b.stem),
            dot((b.xm, x + b.stem * 0.52 + r), r)]


def _j(b: Box):
    x, desc = b.p.xheight, b.p.descender
    hook_rx = b.w * 0.55
    hook_ry = min(hook_rx, 96.0)
    r = b.stem * 0.60
    return [line((b.x1, x), (b.x1, desc + hook_ry), b.stem, cap1="butt"),
            arc((b.x1 - hook_rx, desc + hook_ry), hook_rx, hook_ry,
                D(0), D(-155), b.stem, cap0="butt"),
            dot((b.x1, x + b.stem * 0.52 + r), r)]


def _k(b: Box):
    x, asc = b.p.xheight, b.p.ascender
    joint = (b.x0 + b.stem * 0.15, x * 0.36)
    return [line((b.x0, 0), (b.x0, asc), b.stem),
            line(joint, (b.x1, x), b.stem),
            line(joint, (b.x1, 0), b.stem)]


def _l(b: Box):
    return [line((b.xm, 0), (b.xm, b.p.ascender), b.stem)]


def _m(b: Box):
    x = b.p.xheight
    quarter = b.w / 4
    left_shoulder, joint_y = _arch(b, x, quarter, b.x0 + quarter)
    right_shoulder, _ = _arch(b, x, quarter, b.x1 - quarter)
    return [line((b.x0, 0), (b.x0, x), b.stem), left_shoulder,
            line((b.xm, 0), (b.xm, joint_y), b.stem, cap1="butt"), right_shoulder,
            line((b.x1, 0), (b.x1, joint_y), b.stem, cap1="butt")]


def _n(b: Box):
    x = b.p.xheight
    shoulder, joint_y = _arch(b, x, b.w / 2, b.xm)
    return [line((b.x0, 0), (b.x0, x), b.stem), shoulder,
            line((b.x1, 0), (b.x1, joint_y), b.stem, cap1="butt")]


def _o(b: Box):
    x = b.p.xheight
    return ring((b.xm, x / 2), b.w / 2, b.round_ry(x), b.stem)


def _p(b: Box):
    x = b.p.xheight
    return [line((b.x0, b.p.descender), (b.x0, x / 2), b.stem, cap1="butt")] + \
        ring((b.xm, x / 2), b.w / 2, b.round_ry(x), b.stem)


def _q(b: Box):
    x = b.p.xheight
    return [line((b.x1, b.p.descender), (b.x1, x / 2), b.stem, cap1="butt")] + \
        ring((b.xm, x / 2), b.w / 2, b.round_ry(x), b.stem)


def _r(b: Box):
    x = b.p.xheight
    rx = b.x1 - b.x0
    ry = min(rx, x * 0.44)
    return [line((b.x0, 0), (b.x0, x), b.stem),
            arc((b.x0 + rx, x - ry), rx, ry, D(180), D(58), b.stem, cap0="butt")]


def _s(b: Box):
    return _spine(b, b.p.xheight)


def _t(b: Box):
    x, asc = b.p.xheight, b.p.ascender
    stem_x = b.x0 + b.w * 0.30
    hook_rx = b.x1 - stem_x
    hook_ry = min(hook_rx, x * 0.26)
    return [line((stem_x, asc * 0.90), (stem_x, hook_ry), b.stem, cap1="butt"),
            arc((stem_x + hook_rx, hook_ry), hook_rx, hook_ry,
                D(180), D(280), b.stem, cap0="butt"),
            line((b.x0, x), (b.x1, x), b.stem)]


def _u(b: Box):
    x = b.p.xheight
    rx = b.w / 2
    ry = min(rx, x * 0.46)
    return [line((b.x0, x), (b.x0, ry), b.stem, cap1="butt"),
            arc((b.xm, ry), rx, ry, D(180), D(360), b.stem, cap0="butt", cap1="butt"),
            line((b.x1, x), (b.x1, 0), b.stem)]


def _v(b: Box):
    x = b.p.xheight
    return [line((b.x0, x), (b.xm, 0), b.stem), line((b.xm, 0), (b.x1, x), b.stem)]


def _w(b: Box):
    x = b.p.xheight
    a = b.x0 + b.w * 0.27
    d = b.x1 - b.w * 0.27
    return [line((b.x0, x), (a, 0), b.stem),
            line((a, 0), (b.xm, x * 0.68), b.stem),
            line((b.xm, x * 0.68), (d, 0), b.stem),
            line((d, 0), (b.x1, x), b.stem)]


def _x(b: Box):
    x = b.p.xheight
    return [line((b.x0, 0), (b.x1, x), b.stem), line((b.x1, 0), (b.x0, x), b.stem)]


def _y(b: Box):
    x, desc = b.p.xheight, b.p.descender
    # 右の払いをそのまま下へ伸ばして、ディセンダーまで一気に通す。
    slope_x = (b.x1 - b.xm) / x
    end_x = b.xm - slope_x * abs(desc)
    return [line((b.x0, x), (b.xm, 0), b.stem),
            line((b.x1, x), (max(b.x0, end_x), desc), b.stem)]


def _z(b: Box):
    x = b.p.xheight
    return [line((b.x0, x), (b.x1, x), b.stem),
            line((b.x1, x), (b.x0, 0), b.stem),
            line((b.x0, 0), (b.x1, 0), b.stem)]


LOWERCASE = {
    "a": _a, "b": _b, "c": _c, "d": _d, "e": _e, "f": _f, "g": _g, "h": _h,
    "i": _i, "j": _j, "k": _k, "l": _l, "m": _m, "n": _n, "o": _o, "p": _p,
    "q": _q, "r": _r, "s": _s, "t": _t, "u": _u, "v": _v, "w": _w, "x": _x,
    "y": _y, "z": _z,
}


# --------------------------------------------------------------------------
# 数字
# --------------------------------------------------------------------------

def _zero(b: Box):
    f = b.p.figure
    return ring((b.xm, f / 2), b.w / 2, b.round_ry(f), b.stem)


def _one(b: Box):
    f = b.p.figure
    return [line((b.xm, 0), (b.xm, f), b.stem),
            line((b.xm - b.w * 0.42, f - b.w * 0.42), (b.xm, f), b.stem)]


def _two(b: Box):
    f = b.p.figure
    rx = b.w / 2
    ry = min(rx, f * 0.30)
    cy = f - ry
    end = strokes.ellipse_point(b.xm, cy, rx, ry, D(-40))
    return [arc((b.xm, cy), rx, ry, D(160), D(-40), b.stem),
            line(end, (b.x0, 0), b.stem, cap1="butt"),
            line((b.x0, 0), (b.x1, 0), b.stem)]


def _three(b: Box):
    f = b.p.figure
    rx = b.w / 2
    half = (f + 2 * b.p.overshoot - b.stem) / 2.0
    ry = half / 2.0
    cy = f / 2
    return [arc((b.xm, cy + ry), rx, ry, D(160), D(-70), b.stem),
            arc((b.xm, cy - ry), rx, ry, D(70), D(-160), b.stem)]


def _four(b: Box):
    f = b.p.figure
    bar_y = f * 0.26
    stem_x = b.x1 - b.w * 0.20
    return [line((stem_x, f), (b.x0, bar_y), b.stem, cap1="butt"),
            line((b.x0, bar_y), (b.x1, bar_y), b.stem),
            line((stem_x, 0), (stem_x, f), b.stem)]


def _five(b: Box):
    f = b.p.figure
    rx = b.w / 2
    ry = min(rx, f * 0.33)
    # 縦線は下のふくらみの左端（180 度の位置）まで下ろし、そこから
    # 上を通って右へ回り込ませる。継ぎ目が一直線になるので隙間ができない。
    return [line((b.x0, f), (b.x1, f), b.stem),
            line((b.x0, f), (b.x0, ry), b.stem, cap1="butt"),
            arc((b.xm, ry), rx, ry, D(180), D(-125), b.stem, cap0="butt")]


def _six(b: Box):
    f = b.p.figure
    rx = b.w / 2
    ry = min(rx, f * 0.29)
    big_ry = f - ry
    return ring((b.xm, ry), rx, ry, b.stem) + [
        arc((b.xm, f - big_ry), rx, big_ry, D(180), D(68), b.stem, cap0="butt")]


def _seven(b: Box):
    f = b.p.figure
    return [line((b.x0, f), (b.x1, f), b.stem),
            line((b.x1, f), (b.x0 + b.w * 0.22, 0), b.stem)]


def _eight(b: Box):
    f = b.p.figure
    top_ry = f * 0.23
    bottom_ry = f / 2 - top_ry
    return (ring((b.xm, f - top_ry), b.w / 2 * 0.84, top_ry, b.stem) +
            ring((b.xm, bottom_ry), b.w / 2, bottom_ry, b.stem))


def _nine(b: Box):
    f = b.p.figure
    rx = b.w / 2
    ry = min(rx, f * 0.29)
    big_ry = f - ry
    return ring((b.xm, f - ry), rx, ry, b.stem) + [
        arc((b.xm, big_ry), rx, big_ry, D(0), D(-112), b.stem, cap0="butt")]


DIGITS = {
    "0": _zero, "1": _one, "2": _two, "3": _three, "4": _four,
    "5": _five, "6": _six, "7": _seven, "8": _eight, "9": _nine,
}

# 全設計の索引。
DESIGNS: dict[str, object] = {**CAPITALS, **LOWERCASE, **DIGITS}
