"""
CSV-based quickstart script.
- Generates starter markdown from `items.csv` and `guides.csv` without AI.
- Calls `build_data.py` to refresh `items_data.json` immediately.
"""
import argparse
import csv
import os
from datetime import datetime

from build_data import main as build_json
from item_generator import build_item_slug, finalize_item_markdown, guide_stem_from_topic_en, uniquify_slugs

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SCRIPT_DIR)
CONTENT_DIR = os.path.join(BASE_DIR, "app", "content")
GUIDE_DIR = os.path.join(CONTENT_DIR, "guides")
ITEMS_CSV = os.path.join(SCRIPT_DIR, "csv", "items.csv")
GUIDES_CSV = os.path.join(SCRIPT_DIR, "csv", "guides.csv")


def _write_if_needed(path: str, content: str, force: bool) -> bool:
    if os.path.exists(path) and not force:
        return False
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return True


def _item_markdown(name: str, safe_name: str, lat: str, lng: str, address: str, features: str, agoda: str, lang: str) -> str:
    today = datetime.now().strftime("%Y-%m-%d")
    if lang == "ko":
        title = f"{name}: Korean Guide"
        categories = '["Local Gem"]'
        summary = f"Korean version draft for {name}, with practical highlights."
        body = (
            f"## Introduction\n{name} is a notable place around {address}.\n\n"
            f"## Highlights\n- Features: {features or 'Local atmosphere'}\n- Location: {address}\n\n"
            "## Visitor Tips\nCheck opening hours, queue status, and transit in advance.\n"
        )
    else:
        title = f"{name}: Quick Guide"
        categories = '["Local Gem"]'
        summary = f"A fast overview of {name}, including highlights and practical tips."
        body = (
            f"## Introduction\n{name} is a popular spot around {address}.\n\n"
            f"## Highlights\n- Features: {features or 'Local atmosphere'}\n- Location: {address}\n\n"
            "## Visitor Tips\nCheck opening hours and nearby transit before visiting.\n"
        )

    return f"""---
lang: {lang}
title: "{title}"
lat: {lat}
lng: {lng}
categories: {categories}
thumbnail: "/static/images/{safe_name}.jpg"
address: "{address}"
date: "{today}"
agoda: "{agoda}"
summary: "{summary}"
image_prompt: "Editorial travel photo of {name}, natural light, realistic details."
---

{body}
"""


def _guide_markdown(guide_id: str, topic: str, keywords: str, lang: str) -> str:
    today = datetime.now().strftime("%Y-%m-%d")
    if lang == "ko":
        summary = f"Korean version draft of a practical quick-start guide for {topic}."
        body = (
            f"## Overview\nUse this guide to plan {topic} quickly.\n\n"
            "## Checklist\n- Route\n- Budget\n- Best timing\n\n"
            f"## Keywords\n{keywords or 'travel, japan'}\n"
        )
    else:
        summary = f"A practical quick-start guide for {topic}."
        body = (
            f"## Overview\nUse this quick guide to plan {topic} efficiently.\n\n"
            "## Checklist\n- Route\n- Budget\n- Best timing\n\n"
            f"## Keywords\n{keywords or 'travel, japan'}\n"
        )

    return f"""---
lang: {lang}
title: "{topic}"
summary: "{summary}"
date: "{today}"
---

{body}
"""


def generate_items(force: bool) -> int:
    if not os.path.exists(ITEMS_CSV):
        print(f"❌ items.csv not found: {ITEMS_CSV}")
        return 0

    created = 0
    skipped_invalid_coords = 0
    rows_data: list[tuple[str, str, str, str, str, str]] = []
    with open(ITEMS_CSV, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = (row.get("Name") or "").strip()
            if not name:
                continue
            lat = (row.get("Lat") or "0").strip()
            lng = (row.get("Lng") or "0").strip()
            try:
                lat_num = float(lat)
                lng_num = float(lng)
            except ValueError:
                skipped_invalid_coords += 1
                continue
            if lat_num == 0.0 or lng_num == 0.0:
                skipped_invalid_coords += 1
                continue
            address = (row.get("Address") or "Japan").strip().replace('"', '\\"')
            features = (row.get("Features") or "").strip().replace('"', '\\"')
            agoda = (row.get("Agoda") or "").strip().replace('"', '\\"')
            rows_data.append((name, lat, lng, address, features, agoda))

    slugs = [build_item_slug(name, addr) for name, _, _, addr, _, _ in rows_data]
    safe_names = uniquify_slugs(slugs)

    for safe_name, (name, lat, lng, address, features, agoda) in zip(safe_names, rows_data):
        for lang in ("en", "ko"):
            filename = f"{safe_name}_{lang}.md"
            out_path = os.path.join(CONTENT_DIR, filename)
            content = _item_markdown(name, safe_name, lat, lng, address, features, agoda, lang)
            if _write_if_needed(out_path, content, force):
                created += 1
            finalize_item_markdown(out_path, name)
    if skipped_invalid_coords:
        print(f"⚠️ Skipped items.csv rows due to invalid coordinates: {skipped_invalid_coords}")
    return created


def generate_guides(force: bool) -> int:
    if not os.path.exists(GUIDES_CSV):
        print(f"⚠️ guides.csv not found: {GUIDES_CSV}")
        return 0

    created = 0
    with open(GUIDES_CSV, "r", encoding="utf-8-sig") as f:
        guide_rows = list(csv.DictReader(f))
    stems = uniquify_slugs(
        [guide_stem_from_topic_en((r.get("topic_en") or "").strip()) for r in guide_rows]
    )
    for row, gid in zip(guide_rows, stems):
        topic_en = (row.get("topic_en") or "Guide").strip().replace('"', '\\"')
        topic_ko = (row.get("topic_ko") or "Guide").strip().replace('"', '\\"')
        keywords = (row.get("keywords") or "").strip().replace('"', '\\"')

        en_path = os.path.join(GUIDE_DIR, f"{gid}_en.md")
        ko_path = os.path.join(GUIDE_DIR, f"{gid}_ko.md")
        if _write_if_needed(en_path, _guide_markdown(gid, topic_en, keywords, "en"), force):
            created += 1
        if _write_if_needed(ko_path, _guide_markdown(gid, topic_ko, keywords, "ko"), force):
            created += 1
    return created


def main():
    parser = argparse.ArgumentParser(description="Generate quickstart content from CSV")
    parser.add_argument("--force", action="store_true", help="Overwrite existing markdown files")
    args = parser.parse_args()

    os.makedirs(CONTENT_DIR, exist_ok=True)
    os.makedirs(GUIDE_DIR, exist_ok=True)

    item_count = generate_items(force=args.force)
    guide_count = generate_guides(force=args.force)
    build_json()

    print(f"✅ quickstart done: generated {item_count} item md and {guide_count} guide md files")
    print("👉 Next: python run.py")


if __name__ == "__main__":
    main()
