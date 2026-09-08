#!/usr/bin/env python3
"""Koshin Pop（恒紳ポップ）をビルドする。

  python3 tools/fetch_sources.py   # ベースフォントの取得（初回のみ）
  python3 tools/build.py           # build/ に TTF と WOFF2 を出力

ベースフォントの仮名・漢字アウトラインに bounce.py の「弾ける」変形をかけ、
variants.py で異体字を足し、naming.py で書体情報を差し替える、という流れ。
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from fontTools.ttLib import TTFont  # noqa: E402

import bounce  # noqa: E402
import latin_swap  # noqa: E402
import naming  # noqa: E402
import variants  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SOURCES = ROOT / "sources"
BUILD = ROOT / "build"

# 出力するスタイル -> ベースフォントのファイル名
TARGETS = {
    "Regular": "ZenMaruGothic-Regular.ttf",
    "Bold": "ZenMaruGothic-Bold.ttf",
    "Black": "ZenMaruGothic-Black.ttf",
}


def build_one(style: str, base_name: str, *, woff2: bool = True) -> Path:
    base_path = SOURCES / base_name
    if not base_path.exists():
        raise SystemExit(
            f"ベースフォントがありません: {base_path}\n"
            f"先に `python3 tools/fetch_sources.py` を実行してください。"
        )

    print(f"[{style}] {base_name}")
    started = time.time()
    font = TTFont(base_path)

    replaced = latin_swap.swap_latin(font, style)
    print(f"  オリジナル欧文に差し替え: {len(replaced)} グリフ")

    decomposed = bounce.decompose_composites(font)
    print(f"  合成グリフを展開: {decomposed} グリフ")

    bases = variants.duplicate_glyphs(font)
    print(f"  異体字のもとを複製: {len(bases)} 文字 x {variants.CYCLE - 1} 種")

    print("  弾ける変形を適用")
    bounce.apply_bounce(font, verbose=True)

    print("  異体字の切り替え規則 (calt / ss01 / ss02) を追加")
    variants.add_features(font, bases)

    print("  書体情報を設定")
    naming.apply_names(font, style)
    naming.apply_metadata(font, style)
    ascent, descent = naming.retune_vertical_metrics(font)
    print(f"    上下メトリクス: +{ascent} / -{descent}")

    BUILD.mkdir(parents=True, exist_ok=True)
    ttf_path = BUILD / f"KoshinPop-{style}.ttf"
    font.save(ttf_path)
    print(f"  → {ttf_path.relative_to(ROOT)} ({ttf_path.stat().st_size:,} bytes)")

    if woff2:
        try:
            font.flavor = "woff2"
            woff2_path = BUILD / f"KoshinPop-{style}.woff2"
            font.save(woff2_path)
            print(f"  → {woff2_path.relative_to(ROOT)} ({woff2_path.stat().st_size:,} bytes)")
        except Exception as exc:  # brotli 未導入などで失敗しても TTF は残す
            print(f"  ! WOFF2 の書き出しをスキップしました: {exc}")

    print(f"  {time.time() - started:.1f}s")
    return ttf_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Koshin Pop をビルドする")
    parser.add_argument("styles", nargs="*", default=None,
                        help="ビルドするスタイル (既定: 全部)")
    parser.add_argument("--no-woff2", action="store_true", help="WOFF2 を出力しない")
    args = parser.parse_args()

    styles = args.styles or list(TARGETS)
    unknown = [s for s in styles if s not in TARGETS]
    if unknown:
        raise SystemExit(f"未知のスタイル: {', '.join(unknown)}（{', '.join(TARGETS)} から選択）")

    for style in styles:
        build_one(style, TARGETS[style], woff2=not args.no_woff2)
    print("ビルド完了")
    return 0


if __name__ == "__main__":
    sys.exit(main())
