#!/usr/bin/env python3
"""同じ文字が連続しても表情が変わるようにするための異体字まわり。

やっていることは二段構え。

1. 変形をかける前に、欧文・数字・仮名・約物の各グリフを ".pop1" ".pop2"
   という名前で複製しておく。bounce.py の跳ね方はグリフ名から決まるので、
   複製しただけで自動的に別の跳ね方・傾き・大きさになる。
2. OpenType の calt（文脈依存の異体字）で、直前の文字の状態を見ながら
   基本形 → pop1 → pop2 → 基本形 … と循環させる。

結果として「ああああ」や「LOOOOK」のように同じ字が並んでも、隣り合った
字が同じ形になることがない。手書き風・ポップ系の書体で使われる定番の
手法で、これがあるとないとで「弾んでいる」感じがかなり変わる。
"""
from __future__ import annotations

from copy import deepcopy

from fontTools.otlLib import builder as otl
from fontTools.ttLib import TTFont
from fontTools.ttLib.tables import otTables as ot

import bounce

# 異体字を作る字種。漢字は字数が多すぎるので対象外にしている。
VARIANT_CATEGORIES = ("latin", "digit", "kana", "punct")

# 基本形を含めた循環の段数。
CYCLE = 3

SUFFIXES = [""] + [f".pop{i}" for i in range(1, CYCLE)]

# ss01 / ss02 に付ける表示名。
STYLISTIC_SET_LABELS = {
    "ss01": "Bounce variant 1 — 跳ね方を 1 に固定",
    "ss02": "Bounce variant 2 — 跳ね方を 2 に固定",
}


def duplicate_glyphs(font: TTFont) -> list[str]:
    """異体字のもとになるグリフを複製する。複製元のグリフ名を返す。

    合成グリフを展開したあと（bounce.decompose_composites のあと）に呼ぶこと。
    """
    glyf = font["glyf"]
    hmtx = font["hmtx"]
    vmtx = font.get("vmtx")

    cmap = font.getBestCmap()
    reverse: dict[str, int] = {}
    for codepoint, name in cmap.items():
        reverse.setdefault(name, codepoint)

    order = list(font.getGlyphOrder())
    existing = set(order)
    bases: list[str] = []
    added: list[str] = []

    for name in order:
        if bounce.categorize(reverse.get(name)) not in VARIANT_CATEGORIES:
            continue
        if glyf[name].numberOfContours == 0:
            continue  # 空白は動かしても意味がない
        if any(name + suffix in existing for suffix in SUFFIXES[1:]):
            continue

        bases.append(name)
        for suffix in SUFFIXES[1:]:
            variant = name + suffix
            glyf.glyphs[variant] = deepcopy(glyf[name])
            hmtx[variant] = hmtx[name]
            if vmtx is not None:
                vmtx[variant] = vmtx[name]
            added.append(variant)

    font.setGlyphOrder(order + added)
    font["glyf"].setGlyphOrder(font.getGlyphOrder())
    font["maxp"].numGlyphs = len(font.getGlyphOrder())
    return bases


def _append_lookups(gsub, lookups) -> list[int]:
    lookup_list = gsub.table.LookupList
    first = len(lookup_list.Lookup)
    lookup_list.Lookup.extend(lookups)
    lookup_list.LookupCount = len(lookup_list.Lookup)
    return list(range(first, lookup_list.LookupCount))


def _iter_langsys(gsub):
    for script_record in gsub.table.ScriptList.ScriptRecord:
        script = script_record.Script
        if script.DefaultLangSys is not None:
            yield script.DefaultLangSys
        for record in script.LangSysRecord:
            yield record.LangSys


def _add_feature(gsub, tag: str, lookup_indices: list[int],
                 feature_params=None) -> None:
    """FeatureList にタグ順を保ったまま feature を追加し、全 LangSys に登録する。

    FeatureRecord はタグの昇順に並んでいる必要があるため、挿入位置がずれる
    ぶん既存の LangSys からの参照インデックスも貼り替える。
    """
    feature_list = gsub.table.FeatureList

    record = ot.FeatureRecord()
    record.FeatureTag = tag
    record.Feature = ot.Feature()
    record.Feature.FeatureParams = feature_params
    record.Feature.LookupListIndex = list(lookup_indices)
    record.Feature.LookupCount = len(lookup_indices)

    records = list(feature_list.FeatureRecord) + [record]
    new_order = sorted(range(len(records)), key=lambda i: (records[i].FeatureTag, i))
    remap = {old: new for new, old in enumerate(new_order)}

    feature_list.FeatureRecord = [records[i] for i in new_order]
    feature_list.FeatureCount = len(feature_list.FeatureRecord)
    added_index = remap[len(records) - 1]

    for langsys in _iter_langsys(gsub):
        langsys.FeatureIndex = sorted(remap[i] for i in langsys.FeatureIndex)
        langsys.FeatureIndex.append(added_index)
        langsys.FeatureIndex.sort()
        langsys.FeatureCount = len(langsys.FeatureIndex)
        if langsys.ReqFeatureIndex not in (None, 0xFFFF):
            langsys.ReqFeatureIndex = remap[langsys.ReqFeatureIndex]


def _chain_rule(backtrack: list[str], inputs: list[str], lookup_index: int, glyph_map):
    """「直前が backtrack のどれかなら、input に lookup_index を適用」という規則。"""
    subtable = ot.ChainContextSubst()
    subtable.Format = 3
    subtable.BacktrackGlyphCount = 1
    subtable.BacktrackCoverage = [otl.buildCoverage(set(backtrack), glyph_map)]
    subtable.InputGlyphCount = 1
    subtable.InputCoverage = [otl.buildCoverage(set(inputs), glyph_map)]
    subtable.LookAheadGlyphCount = 0
    subtable.LookAheadCoverage = []

    record = ot.SubstLookupRecord()
    record.SequenceIndex = 0
    record.LookupListIndex = lookup_index
    subtable.SubstCount = 1
    subtable.SubstLookupRecord = [record]
    return subtable


def _stylistic_set_params(font: TTFont, label: str):
    name_table = font["name"]
    name_id = name_table.addName(label, minNameID=255)
    params = ot.FeatureParamsStylisticSet()
    params.Version = 0
    params.UINameID = name_id
    return params


def add_features(font: TTFont, bases: list[str]) -> None:
    """calt と ss01 / ss02 を GSUB に追加する。"""
    if not bases:
        return

    gsub = font["GSUB"]
    glyph_map = font.getReverseGlyphMap()

    cycles = [[name + suffix for name in bases] for suffix in SUFFIXES]

    # 基本形を 1 段目 / 2 段目へ送る単独置換。ss01 / ss02 からも使い回す。
    step_lookups = [
        otl.buildLookup([otl.buildSingleSubstSubtable(dict(zip(cycles[0], cycles[step])))])
        for step in range(1, CYCLE)
    ]
    step_indices = _append_lookups(gsub, step_lookups)

    # 循環に参加しないグリフ（漢字・記号など）は「状態 0」とみなす。
    # そうしておくと漢字をまたいでも仮名の表情が変わり続ける。
    moved = set().union(*(set(c) for c in cycles[1:]))
    state0 = [name for name in font.getGlyphOrder() if name not in moved]

    rules = [_chain_rule(state0, cycles[0], step_indices[0], glyph_map)]
    for step in range(1, CYCLE - 1):
        rules.append(_chain_rule(cycles[step], cycles[0], step_indices[step], glyph_map))
    # 最終段の直後は規則に当たらないので、基本形に戻って循環する。

    calt_indices = _append_lookups(gsub, [otl.buildLookup(rules)])
    _add_feature(gsub, "calt", calt_indices)

    for step, lookup_index in enumerate(step_indices, start=1):
        tag = f"ss{step:02d}"
        _add_feature(gsub, tag, [lookup_index],
                     feature_params=_stylistic_set_params(font, STYLISTIC_SET_LABELS[tag]))
