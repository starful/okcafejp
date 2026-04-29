"""
기존 MD/썸네일을 새 URL 규칙(숫자 없는 stem)으로 옮깁니다. 실행 후: python script/build_data.py
"""
import csv
import os
import shutil

from item_generator import (
    build_item_slug,
    guide_stem_from_topic_en,
    ok_series_slug_segment,
    uniquify_slugs,
)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SCRIPT_DIR)
CONTENT_DIR = os.path.join(BASE_DIR, "app", "content")
GUIDE_DIR = os.path.join(CONTENT_DIR, "guides")
IMAGES_DIR = os.path.join(BASE_DIR, "app", "static", "images")
ITEMS_CSV = os.path.join(SCRIPT_DIR, "csv", "items.csv")
GUIDES_CSV = os.path.join(SCRIPT_DIR, "csv", "guides.csv")


def _legacy_build_item_slug(name: str, address: str) -> str:
    name_part = ok_series_slug_segment(name)
    parts = [p.strip() for p in (address or "").split(",") if p.strip()]
    loc_part = "_".join(ok_series_slug_segment(p) for p in parts) if parts else "japan"
    if not name_part:
        return loc_part
    return f"{name_part}_{loc_part}"


def _legacy_uniquify_numeric(slugs: list[str]) -> list[str]:
    counts: dict[str, int] = {}
    out: list[str] = []
    for s in slugs:
        counts[s] = counts.get(s, 0) + 1
        n = counts[s]
        out.append(s if n == 1 else f"{s}_{n}")
    return out


def _patch_thumbnail(text: str, old_base: str, new_base: str) -> str:
    return text.replace(
        f"/static/images/{old_base}.jpg",
        f"/static/images/{new_base}.jpg",
    )


def migrate_items() -> int:
    if not os.path.exists(ITEMS_CSV):
        return 0
    rows: list[dict] = []
    with open(ITEMS_CSV, "r", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            if not (row.get("Name") or "").strip():
                continue
            rows.append(row)

    old_slugs = _legacy_uniquify_numeric(
        [_legacy_build_item_slug(r.get("Name", ""), r.get("Address", "")) for r in rows]
    )
    new_slugs = uniquify_slugs([build_item_slug(r.get("Name", ""), r.get("Address", "")) for r in rows])

    n = 0
    for old_b, new_b in zip(old_slugs, new_slugs):
        if old_b == new_b:
            continue
        for lang in ("en", "ko"):
            op = os.path.join(CONTENT_DIR, f"{old_b}_{lang}.md")
            np = os.path.join(CONTENT_DIR, f"{new_b}_{lang}.md")
            if not os.path.exists(op):
                continue
            with open(op, "r", encoding="utf-8") as f:
                body = f.read()
            body = _patch_thumbnail(body, old_b, new_b)
            if os.path.exists(np):
                os.remove(np)
            with open(np, "w", encoding="utf-8") as f:
                f.write(body)
            os.remove(op)
            n += 1
        oj = os.path.join(IMAGES_DIR, f"{old_b}.jpg")
        nj = os.path.join(IMAGES_DIR, f"{new_b}.jpg")
        if os.path.exists(oj) and not os.path.exists(nj):
            shutil.move(oj, nj)
        elif os.path.exists(oj) and os.path.exists(nj):
            try:
                os.remove(oj)
            except OSError:
                pass
    return n


def migrate_guides() -> int:
    if not os.path.exists(GUIDES_CSV):
        return 0
    with open(GUIDES_CSV, "r", encoding="utf-8-sig") as f:
        guide_rows = list(csv.DictReader(f))
    old_ids = [(r.get("id") or "").strip() for r in guide_rows]
    new_ids = uniquify_slugs(
        [guide_stem_from_topic_en((r.get("topic_en") or "").strip()) for r in guide_rows]
    )
    n = 0
    for old_b, new_b in zip(old_ids, new_ids):
        if not old_b or old_b == new_b:
            continue
        for lang in ("en", "ko"):
            op = os.path.join(GUIDE_DIR, f"{old_b}_{lang}.md")
            np = os.path.join(GUIDE_DIR, f"{new_b}_{lang}.md")
            if not os.path.exists(op):
                continue
            if os.path.exists(np):
                os.remove(np)
            shutil.move(op, np)
            n += 1
    return n


def main():
    os.makedirs(GUIDE_DIR, exist_ok=True)
    mi = migrate_items()
    mg = migrate_guides()
    print(f"✅ Migrated item files touched: {mi}, guide files renamed: {mg}")
    print("👉 Run: python script/build_data.py")


if __name__ == "__main__":
    main()
