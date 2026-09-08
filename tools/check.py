#!/usr/bin/env python3
"""ビルドしたフォントの検証。

  python3 tools/check.py            # build/ の全 TTF を検査
  python3 tools/check.py build/KoshinPop-Bold.ttf

字が欠けていないか、跳ね上げた字面がメトリクスからはみ出していないか、
異体字の切り替えが実際に効いているかを確認する。
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from fontTools.ttLib import TTFont  # noqa: E402

import naming  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent

REQUIRED_TABLES = ("cmap", "glyf", "head", "hhea", "hmtx", "maxp", "name",
                   "OS/2", "post", "GSUB")

# 最低限そろっていてほしい文字。第一水準漢字は全部は見ないので代表例を置く。
REQUIRED_TEXT = (
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    "abcdefghijklmnopqrstuvwxyz"
    "0123456789"
    "!?#$%&()*+,-./:;<=>@[]^_{|}~"
    "あいうえおかきくけこさしすせそたちつてとなにぬねのはひふへほまみむめもやゆよらりるれろわをん"
    "ぁぃぅぇぉっゃゅょがざだばぱ"
    "アイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホマミムメモヤユヨラリルレロワヲンヴ"
    "ー、。「」・〜（）"
    "日本語弾恒紳春夏秋冬月火水木金土曜東京都道府県令和西暦年号"
    "一二三四五六七八九十百千万円人口山川空海森林田畑"
    "０１２３４５６７８９ＡＢＣａｂｃ"
)

# 異体字が切り替わることを確かめる文字列。
CYCLE_SAMPLES = ("ああああ", "LOOOOK", "0000", "！！！")


class Report:
    def __init__(self) -> None:
        self.failures: list[str] = []

    def check(self, ok: bool, label: str, detail: str = "") -> None:
        mark = "OK  " if ok else "NG  "
        print(f"  {mark}{label}{(' — ' + detail) if detail else ''}")
        if not ok:
            self.failures.append(label)


def check_font(path: Path, report: Report) -> None:
    print(f"[{path.name}]")
    font = TTFont(path)

    missing_tables = [t for t in REQUIRED_TABLES if t not in font]
    report.check(not missing_tables, "必要なテーブルがそろっている",
                 f"欠落: {missing_tables}" if missing_tables else "")

    cmap = font.getBestCmap()
    missing_chars = sorted({c for c in REQUIRED_TEXT if ord(c) not in cmap})
    report.check(not missing_chars, "必須の文字がすべて収録されている",
                 f"欠落: {''.join(missing_chars)}" if missing_chars else
                 f"{len(set(REQUIRED_TEXT))} 文字を確認")

    glyf = font["glyf"]
    blank = [c for c in REQUIRED_TEXT if not c.isspace()
             and glyf[cmap[ord(c)]].numberOfContours == 0] if not missing_chars else []
    report.check(not blank, "必須の文字に空グリフがない",
                 f"空: {''.join(blank)}" if blank else "")

    os2 = font["OS/2"]
    top = bottom = 0
    for name in font.getGlyphOrder():
        glyph = glyf[name]
        if glyph.numberOfContours == 0:
            continue
        glyph.recalcBounds(glyf)
        top = max(top, glyph.yMax)
        bottom = min(bottom, glyph.yMin)
    report.check(top <= os2.usWinAscent and -bottom <= os2.usWinDescent,
                 "字面が上下メトリクスに収まっている",
                 f"字面 +{top}/{bottom} vs メトリクス +{os2.usWinAscent}/-{os2.usWinDescent}")

    name_table = font["name"]
    family = name_table.getDebugName(16) or name_table.getDebugName(1)
    report.check(family == naming.FAMILY, "ファミリー名が正しい", f"{family}")
    report.check(bool(name_table.getDebugName(13)), "ライセンス表記が入っている")
    report.check(name_table.getDebugName(14) == naming.LICENSE_URL,
                 "ライセンス URL が入っている")
    report.check(os2.fsType == 0, "埋め込み制限がない (fsType=0)")

    features = {r.FeatureTag for r in font["GSUB"].table.FeatureList.FeatureRecord}
    report.check({"calt", "ss01", "ss02"} <= features,
                 "異体字の feature が登録されている", ", ".join(sorted(features)))

    check_shaping(path, font, report)


def check_shaping(path: Path, font: TTFont, report: Report) -> None:
    try:
        import uharfbuzz as hb
    except ImportError:
        print("  --  シェーピング検査はスキップ（uharfbuzz 未導入）")
        return

    hb_font = hb.Font(hb.Face(hb.Blob.from_file_path(str(path))))
    order = font.getGlyphOrder()

    def shape(text: str) -> list[str]:
        buf = hb.Buffer()
        buf.add_str(text)
        buf.guess_segment_properties()
        hb.shape(hb_font, buf)
        return [order[info.codepoint] for info in buf.glyph_infos]

    for sample in CYCLE_SAMPLES:
        glyphs = shape(sample)
        varied = len(set(glyphs)) > 1
        report.check(varied, f"同じ文字の連続で字形が変わる: {sample}", " ".join(glyphs))


def main() -> int:
    paths = [Path(a) for a in sys.argv[1:]] or sorted((ROOT / "build").glob("*.ttf"))
    if not paths:
        raise SystemExit("検査対象がありません。先に tools/build.py を実行してください。")

    report = Report()
    for path in paths:
        check_font(path, report)
        print()

    if report.failures:
        print(f"NG が {len(report.failures)} 件あります: {', '.join(report.failures)}")
        return 1
    print("すべての検査に通りました。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
