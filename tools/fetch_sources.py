#!/usr/bin/env python3
"""ベースフォント（Zen Maru Gothic / SIL Open Font License 1.1）を sources/ に取得する。

Koshin Pop は Zen Maru Gothic の派生フォントとして仮名・漢字のアウトラインを継承する。
再配布可能なライセンスだが、リポジトリには原本を含めずビルド時に取得する方式にしている。
"""
from __future__ import annotations

import hashlib
import sys
import urllib.request
from pathlib import Path

SOURCES_DIR = Path(__file__).resolve().parent.parent / "sources"

# Google Fonts の静的 TTF。weight ごとに配信 URL が異なる。
BASE_FONTS = {
    "ZenMaruGothic-Regular.ttf": "https://fonts.gstatic.com/s/zenmarugothic/v19/o-0SIpIxzW5b-RxT-6A8jWAtCp-k7Q.ttf",
    "ZenMaruGothic-Bold.ttf": "https://fonts.gstatic.com/s/zenmarugothic/v19/o-0XIpIxzW5b-RxT-6A8jWAtCp-cUW1CPA.ttf",
    "ZenMaruGothic-Black.ttf": "https://fonts.gstatic.com/s/zenmarugothic/v19/o-0XIpIxzW5b-RxT-6A8jWAtCp-caW9CPA.ttf",
}

# 取得したファイルが差し替わっていないことの確認用。Google Fonts 側で
# ベースフォントが更新された場合はここが一致しなくなるので、字形の変化を
# 確認したうえで書き換えること。
EXPECTED_SHA256: dict[str, str] = {
    "ZenMaruGothic-Black.ttf":
        "063367e350e7c8221e0e12ed590910a7814f84bb2826e284db0505317ef4b6e6",
    "ZenMaruGothic-Bold.ttf":
        "cd35e29918e3b485606211f7f8e7fac943a2e46422868f55fcadb45e1011ddb8",
    "ZenMaruGothic-Regular.ttf":
        "fea6d7937b375090353e9df58987b784bb807ca8aa2e28d9c0c018f13ee21221",
}


def fetch(name: str, url: str) -> Path:
    dest = SOURCES_DIR / name
    if dest.exists():
        print(f"  skip   {name} (取得済み)")
        return dest

    print(f"  fetch  {name}")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=180) as res:
        data = res.read()

    digest = hashlib.sha256(data).hexdigest()
    expected = EXPECTED_SHA256.get(name)
    if expected and expected != digest:
        raise SystemExit(f"{name}: sha256 が一致しません (期待 {expected} / 実際 {digest})")

    dest.write_bytes(data)
    print(f"         {len(data):,} bytes  sha256={digest}")
    return dest


def main() -> int:
    SOURCES_DIR.mkdir(parents=True, exist_ok=True)
    print("ベースフォントを取得します (SIL Open Font License 1.1)")
    for name, url in BASE_FONTS.items():
        fetch(name, url)
    print("完了")
    return 0


if __name__ == "__main__":
    sys.exit(main())
