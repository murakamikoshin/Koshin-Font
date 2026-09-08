#!/usr/bin/env python3
"""骨格線に丸い線幅を与えてアウトラインを作るための幾何ライブラリ。

Koshin Pop の欧文は「線を引いて太らせる」やり方で設計している。直線と
楕円弧に丸い端点（ラウンドキャップ）を付けた閉曲線を重ねて置き、
TrueType の nonzero 塗りつぶしで自然に合体させる。この方式だと

  * 線の太さを変えるだけでウェイト展開ができる
  * 骨格の座標だけで字形を記述できるので調整が速い

という利点があり、丸ゴシック系の字形とは相性がよい。
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from fontTools.pens.areaPen import AreaPen
from fontTools.pens.recordingPen import RecordingPen
from fontTools.pens.reverseContourPen import ReverseContourPen

# 楕円弧を二次ベジェで近似するときの 1 セグメントあたりの最大角度。
MAX_ARC_STEP = math.radians(30)

Point = tuple[float, float]


@dataclass
class Contour:
    """閉曲線ひとつ。start から始まり segments をたどって閉じる。"""

    start: Point
    segments: list = field(default_factory=list)  # ("l", pt) / ("q", ctrl, pt)
    hole: bool = False

    def line_to(self, pt: Point) -> None:
        self.segments.append(("l", pt))

    def curve_to(self, ctrl: Point, pt: Point) -> None:
        self.segments.append(("q", ctrl, pt))

    def draw(self, pen) -> None:
        pen.moveTo(self.start)
        for segment in self.segments:
            if segment[0] == "l":
                pen.lineTo(segment[1])
            else:
                pen.qCurveTo(segment[1], segment[2])
        pen.closePath()


def ellipse_point(cx: float, cy: float, rx: float, ry: float, angle: float) -> Point:
    return cx + rx * math.cos(angle), cy + ry * math.sin(angle)


def _arc_segments(contour: Contour, cx: float, cy: float, rx: float, ry: float,
                  a0: float, a1: float) -> None:
    """a0 から a1 までの楕円弧を二次ベジェで追加する（現在位置は a0 の点）。"""
    sweep = a1 - a0
    if abs(sweep) < 1e-12:
        return
    steps = max(1, math.ceil(abs(sweep) / MAX_ARC_STEP))
    delta = sweep / steps
    # 接線の交点までの距離。楕円は円のアフィン変換なので同じ係数が使える。
    k = 1.0 / math.cos(delta / 2.0)
    for i in range(steps):
        start_angle = a0 + delta * i
        end_angle = start_angle + delta
        mid_angle = start_angle + delta / 2.0
        ctrl = (cx + rx * k * math.cos(mid_angle), cy + ry * k * math.sin(mid_angle))
        contour.curve_to(ctrl, ellipse_point(cx, cy, rx, ry, end_angle))


def _cap(contour: Contour, center: Point, start: Point, outward: Point) -> None:
    """start から center を中心に半円を描いて反対側へ回る（ラウンドキャップ）。"""
    cx, cy = center
    radius = math.hypot(start[0] - cx, start[1] - cy)
    if radius < 1e-9:
        return
    a0 = math.atan2(start[1] - cy, start[0] - cx)
    # 半円の頂点が outward 方向を向くように回る向きを選ぶ。
    target = math.atan2(outward[1], outward[0])
    forward = (a0 + math.pi / 2.0 - target + math.pi) % (2 * math.pi) - math.pi
    sweep = math.pi if abs(forward) < math.pi / 2.0 else -math.pi
    _arc_segments(contour, cx, cy, radius, radius, a0, a0 + sweep)


def line(p0: Point, p1: Point, width: float,
         cap0: str = "round", cap1: str = "round") -> Contour:
    """p0-p1 の直線を太さ width に太らせた閉曲線。cap は "round" か "butt"。"""
    half = width / 2.0
    dx, dy = p1[0] - p0[0], p1[1] - p0[1]
    length = math.hypot(dx, dy)
    if length < 1e-9:
        dx, dy, length = 1.0, 0.0, 1.0
    ux, uy = dx / length, dy / length
    nx, ny = -uy * half, ux * half  # 左手側の法線

    a = (p0[0] + nx, p0[1] + ny)
    b = (p1[0] + nx, p1[1] + ny)
    c = (p1[0] - nx, p1[1] - ny)
    d = (p0[0] - nx, p0[1] - ny)

    contour = Contour(start=a)
    contour.line_to(b)
    if cap1 == "round":
        _cap(contour, p1, b, (ux, uy))
    else:
        contour.line_to(c)
    contour.line_to(d)
    if cap0 == "round":
        _cap(contour, p0, d, (-ux, -uy))
    else:
        contour.line_to(a)
    return contour


def arc(center: Point, rx: float, ry: float, a0: float, a1: float, width: float,
        cap0: str = "round", cap1: str = "round") -> Contour:
    """中心 center・半径 (rx, ry) の楕円弧を太さ width に太らせた閉曲線。"""
    cx, cy = center
    half = width / 2.0
    outer = (rx + half, ry + half)
    inner = (max(rx - half, 1.0), max(ry - half, 1.0))
    forward = 1.0 if a1 >= a0 else -1.0

    start = ellipse_point(cx, cy, outer[0], outer[1], a0)
    contour = Contour(start=start)
    _arc_segments(contour, cx, cy, outer[0], outer[1], a0, a1)

    end_mid = ellipse_point(cx, cy, rx, ry, a1)
    tangent = (-rx * math.sin(a1) * forward, ry * math.cos(a1) * forward)
    if cap1 == "round":
        _cap(contour, end_mid, ellipse_point(cx, cy, outer[0], outer[1], a1), tangent)
    else:
        contour.line_to(ellipse_point(cx, cy, inner[0], inner[1], a1))
    _arc_segments(contour, cx, cy, inner[0], inner[1], a1, a0)

    start_mid = ellipse_point(cx, cy, rx, ry, a0)
    if cap0 == "round":
        back = (rx * math.sin(a0) * forward, -ry * math.cos(a0) * forward)
        _cap(contour, start_mid, ellipse_point(cx, cy, inner[0], inner[1], a0), back)
    else:
        contour.line_to(start)
    return contour


def ring(center: Point, rx: float, ry: float, width: float) -> list[Contour]:
    """閉じた輪（o や O の骨格）。外側と内側の 2 本の閉曲線を返す。"""
    cx, cy = center
    half = width / 2.0
    outer = Contour(start=(cx + rx + half, cy))
    _arc_segments(outer, cx, cy, rx + half, ry + half, 0.0, 2 * math.pi)
    inner = Contour(start=(cx + rx - half, cy), hole=True)
    _arc_segments(inner, cx, cy, max(rx - half, 1.0), max(ry - half, 1.0), 0.0, 2 * math.pi)
    return [outer, inner]


def dot(center: Point, radius: float) -> Contour:
    cx, cy = center
    contour = Contour(start=(cx + radius, cy))
    _arc_segments(contour, cx, cy, radius, radius, 0.0, 2 * math.pi)
    return contour


def draw_contours(contours: list[Contour], pen) -> None:
    """向きをそろえて（外側は時計回り、穴は反時計回り）ペンに描画する。

    重なった閉曲線は nonzero 塗りで合体するので、線どうしの接続部を
    個別に処理する必要がない。
    """
    for contour in contours:
        recorder = RecordingPen()
        contour.draw(recorder)

        area_pen = AreaPen()
        recorder.replay(area_pen)
        area = area_pen.value  # 反時計回りが正

        want_clockwise = not contour.hole
        is_clockwise = area < 0
        if is_clockwise == want_clockwise:
            recorder.replay(pen)
        else:
            recorder.replay(ReverseContourPen(pen))
