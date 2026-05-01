"""
OK Series shared item content generator.
"""
import argparse
import glob
import os
import csv
import re
import time
import concurrent.futures
import urllib.parse
from datetime import datetime

import frontmatter
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.environ.get("GEMINI_API_KEY")

# OK 시리즈 유료 키 기준: okcaddie/oksushi 장문은 gemini-2.5-flash, okramen 라멘은 gemini-flash-latest
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
# 병렬도: okonsen 주석 기준 유료 키 5~10 적당 → oktemplate/okramen 아이템은 5
ITEM_MAX_WORKERS = int(os.environ.get("GEMINI_MAX_WORKERS", "5"))

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SCRIPT_DIR)
CONTENT_DIR = os.path.join(BASE_DIR, "app", "content")

PROMPT_CONFIG = {
    "item_type": "Cafe",
    "item_type_ko": "Cafe",
    "categories": {
        "en": ["Specialty", "Dessert", "Work-Friendly", "Scenic", "Vintage", "Roastery"],
        "ko": ["Specialty", "Dessert", "Work-Friendly", "Scenic", "Vintage", "Roastery"],
    },
    "min_length": 7000,
    "max_length": 8000,
}


def ok_series_slug_segment(text: str) -> str:
    """Match okramen / okcaddie stems: lower, spaces→underscore, strip common punctuation."""
    t = (text or "").lower().strip()
    t = t.replace(" ", "_").replace("'", "").replace(",", "")
    t = t.replace("&", "and").replace(".", "")
    t = t.replace("-", "_")
    return t


def slug_for_url(text: str) -> str:
    """URL/파일 stem용: ok 시리즈 규칙 후 괄호·대괄호 구간 제거, 숫자 제거. `/item/{stem}_en` 과 동일."""
    s = ok_series_slug_segment(text)
    s = re.sub(r"\([^)]*\)", "", s)
    s = re.sub(r"\[[^\]]*\]", "", s)
    s = re.sub(r"\d+", "", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s or "place"


def build_item_slug(name: str, address: str) -> str:
    """이름+주소 기반 stem — 숫자 없음, 위치로 구분(okramen은 이름만; 카페는 동명이인 방지용)."""
    name_part = slug_for_url(name)
    parts = [p.strip() for p in (address or "").split(",") if p.strip()]
    loc_tokens = [slug_for_url(p) for p in parts]
    loc_part = "_".join(t for t in loc_tokens if t) if loc_tokens else "japan"
    if not name_part:
        return loc_part
    return f"{name_part}_{loc_part}"


def uniquify_slugs(slugs: list[str]) -> list[str]:
    """충돌 시 `_2` 대신 `_b`, `_c`, … (URL에 숫자 안 붙음)."""
    counts: dict[str, int] = {}
    out: list[str] = []
    for s in slugs:
        counts[s] = counts.get(s, 0) + 1
        n = counts[s]
        if n == 1:
            out.append(s)
        else:
            suffix = chr(ord("b") + n - 2)
            if suffix > "z":
                suffix = "z"
            out.append(f"{s}_{suffix}")
    return out


def guide_stem_from_topic_en(topic_en: str) -> str:
    """가이드 파일명·URL stem: topic_en 기준, 숫자 제거(ok 시리즈와 동일한 토큰 규칙)."""
    return slug_for_url(topic_en)


def normalize_display_name(name: str) -> str:
    """콘텐츠 노출용 이름: 끝의 구식 번호 코드(예: 001) 제거."""
    cleaned = re.sub(r"\s+0\d\d$", "", (name or "").strip())
    return cleaned or (name or "").strip()


def build_maps_search_url(lat: float, lng: float, label: str = "") -> str:
    """Open Google Maps search near coordinates (not an official place permalink)."""
    label = (label or "").strip()
    if label:
        q = f"{label} @ {lat},{lng}"
    else:
        q = f"{lat},{lng}"
    return "https://www.google.com/maps/search/?api=1&query=" + urllib.parse.quote(q, safe="")


def _trust_copy(lang: str) -> tuple[str, str]:
    """(editorial_note, illustration_note) for the given article lang."""
    if lang == "ko":
        return (
            "본 글은 여행 계획용 에디토리얼 콘텐츠입니다. 매장 공식 페이지가 아니므로 영업 시간·위치·메뉴·가격은 방문 전 지도 링크 또는 현지에서 반드시 확인해 주세요.",
            "상단 이미지는 이해를 돕기 위한 AI 생성 예시 이미지이며, 실제 매장의 인테리어·메뉴와 다를 수 있습니다.",
        )
    return (
        "This page is editorial trip-planning content, not the venue's official site. Always confirm hours, access, menus, and prices on site or via Maps before visiting.",
        "The lead image is an AI-generated illustration and may not show this venue's real interior or offerings.",
    )


def finalize_item_markdown(path: str, csv_venue_name: str | None = None) -> None:
    """Merge venue_name (optional), maps_url, and transparency notes into item frontmatter."""
    with open(path, "r", encoding="utf-8") as f:
        raw = f.read()
    raw = clean_ai_response(raw)
    post = frontmatter.loads(raw)
    if csv_venue_name is not None:
        post["venue_name"] = normalize_display_name(csv_venue_name)
    lang = str(post.get("lang") or "en")
    try:
        lat = float(post.get("lat") or 0)
        lng = float(post.get("lng") or 0)
    except (TypeError, ValueError):
        lat, lng = 0.0, 0.0
    label = str(post.get("venue_name") or "").strip()
    if lat != 0.0 and lng != 0.0:
        post["maps_url"] = build_maps_search_url(lat, lng, label)
    ed, ill = _trust_copy(lang)
    post["editorial_note"] = ed
    post["illustration_note"] = ill
    with open(path, "w", encoding="utf-8") as f:
        f.write(frontmatter.dumps(post))


def ensure_venue_name_in_md(path: str, csv_name: str) -> None:
    """Set venue_name from CSV and refresh trust metadata."""
    finalize_item_markdown(path, csv_name)


def _generate_content_with_retry(client, model: str, prompt: str, max_attempts: int = 8):
    last_err: Exception | None = None
    for attempt in range(max_attempts):
        try:
            return client.models.generate_content(model=model, contents=prompt)
        except Exception as e:
            last_err = e
            msg = str(e).lower()
            if "429" in str(e) or "resource_exhausted" in msg or "resource exhausted" in msg:
                wait = min(120, 8 * (2**attempt))
                print(f"⏳ Rate limited, sleep {wait}s ({attempt + 1}/{max_attempts})...")
                time.sleep(wait)
            else:
                raise
    assert last_err is not None
    raise last_err


def clean_ai_response(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```[a-z]*\n", "", text)
    text = re.sub(r"\n```$", "", text)
    text = re.sub(r"^(##\s*)?yaml\n", "", text, flags=re.IGNORECASE)
    if "---" in text and not text.startswith("---"):
        text = "---" + text.split("---", 1)[1]
    return text.strip()


def ensure_venue_name_in_md(path: str, csv_name: str) -> None:
    """Set frontmatter venue_name from CSV (short display name). SEO title stays in title."""
    display = normalize_display_name(csv_name)
    with open(path, "r", encoding="utf-8") as f:
        raw = f.read()
    raw = clean_ai_response(raw)
    post = frontmatter.loads(raw)
    post["venue_name"] = display
    with open(path, "w", encoding="utf-8") as f:
        f.write(frontmatter.dumps(post))


def _build_prompt(base_id: str, name: str, lat: str, lng: str, address: str, lang: str, features: str, agoda: str) -> str:
    display_name = normalize_display_name(name)
    cat_list = ", ".join(PROMPT_CONFIG["categories"][lang])
    item_type = PROMPT_CONFIG["item_type"] if lang == "en" else PROMPT_CONFIG["item_type_ko"]
    min_len = PROMPT_CONFIG["min_length"]
    max_len = PROMPT_CONFIG["max_length"]
    return f"""
You are an expert travel writer. Write a detailed, SEO-optimized guide for '{display_name}'.
The article body must be between {min_len} and {max_len} characters.

[Target Info]
- Name: {display_name}
- Type: {item_type}
- Location: {address}
- Features: {features}
- Language: {lang}

[Categorization Task]
Select 1-3 categories from: [{cat_list}]

[Output Format - STRICT]
---
lang: {lang}
title: "Compelling SEO title with {display_name} and {address}"
lat: {lat}
lng: {lng}
categories: ["Category1", "Category2"]
thumbnail: "/static/images/{base_id}.jpg"
address: "{address}"
date: "{datetime.now().strftime('%Y-%m-%d')}"
agoda: "{agoda}"
summary: "2-3 sentence hook on one line."
image_prompt: "Single-line Imagen prompt in English for a realistic cafe photo of {display_name}, including composition, lighting, and details based on {features}."
---

[Article Structure]
## Introduction
## Main Feature Analysis
## Visitor Experience
## Practical Information
## Conclusion

IMPORTANT:
- Do NOT use markdown code blocks.
- Start directly with '---'.
- Keep article body length between {min_len} and {max_len} characters.
- Never include legacy numeric name codes like 001/002/003 in title or body.
- Do NOT invent phone numbers, URLs, prices, menus, or opening hours. If unsure, use cautious wording ("often", "typically") and steer readers to verify on site.
- This is not the venue's official listing; avoid claiming verification or partnership unless true.
"""


def generate_item_article(base_id: str, name: str, lat: str, lng: str, address: str, lang: str, features: str, agoda: str = ""):
    if not API_KEY:
        print("❌ GEMINI_API_KEY is missing")
        return

    try:
        from google import genai
        client = genai.Client(api_key=API_KEY)
    except ImportError:
        print("❌ google-genai package is missing: pip install google-genai")
        return

    filename = f"{base_id}_{lang}.md"
    print(f"🚀 [AI] Generating {filename} from '{name}'...")
    prompt = _build_prompt(base_id, name, lat, lng, address, lang, features, agoda)

    try:
        final_text = ""
        for _ in range(5):
            response = _generate_content_with_retry(client, GEMINI_MODEL, prompt)
            final_text = clean_ai_response(response.text)
            if len(final_text) >= PROMPT_CONFIG["min_length"]:
                break
        if len(final_text) < PROMPT_CONFIG["min_length"]:
            print(f"❌ [Failed] {filename}: too short ({len(final_text)} chars)")
            return
        os.makedirs(CONTENT_DIR, exist_ok=True)
        out_path = os.path.join(CONTENT_DIR, filename)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(final_text)
        finalize_item_markdown(out_path, name)
        print(f"✅ [Done] {filename} ({len(final_text):,} chars)")
    except Exception as e:
        print(f"❌ [Failed] {filename}: {e}")


def run_generator(limit: int | None = 10):
    """limit=None or limit<=0 means process every row in items.csv."""
    csv_path = os.path.join(SCRIPT_DIR, "csv", "items.csv")
    if not os.path.exists(csv_path):
        print(f"❌ CSV not found: {csv_path}")
        return

    max_rows = None if limit is None or limit <= 0 else limit

    parsed: list[tuple[str, str, str, str, str, str]] = []
    with open(csv_path, mode="r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = (row.get("Name") or "").strip()
            if not name:
                continue
            address = (row.get("Address") or "Japan").strip()
            parsed.append(
                (
                    name,
                    row.get("Lat", "0"),
                    row.get("Lng", "0"),
                    address,
                    row.get("Features", ""),
                    row.get("Agoda", ""),
                )
            )
            if max_rows is not None and len(parsed) >= max_rows:
                break

    if not parsed:
        print("❌ No rows to process in items.csv")
        return

    slugs = [build_item_slug(name, addr) for name, _, _, addr, _, _ in parsed]
    base_ids = uniquify_slugs(slugs)

    tasks = []
    for base_id, (name, lat, lng, address, features, agoda) in zip(base_ids, parsed):
        for lang in ["en", "ko"]:
            out_path = os.path.join(CONTENT_DIR, f"{base_id}_{lang}.md")
            if not os.path.exists(out_path):
                tasks.append((base_id, name, lat, lng, address, lang, features, agoda))

    if not tasks:
        print("✨ No new items to generate.")
        return

    print(
        f"🔔 Starting generation for {len(tasks)} files "
        f"(model={GEMINI_MODEL}, workers={ITEM_MAX_WORKERS}, 429 retry)..."
    )
    with concurrent.futures.ThreadPoolExecutor(max_workers=ITEM_MAX_WORKERS) as ex:
        ex.map(lambda p: generate_item_article(*p), tasks)


def enrich_trust_metadata_all_items() -> int:
    """Add / refresh maps_url + editorial notes on all item markdown in content root."""
    n = 0
    for pattern in ("*_en.md", "*_ko.md"):
        for path in sorted(glob.glob(os.path.join(CONTENT_DIR, pattern))):
            finalize_item_markdown(path, csv_venue_name=None)
            n += 1
    print(f"✅ Trust metadata refreshed on {n} item files")
    return n


def _parse_cli_and_run() -> None:
    parser = argparse.ArgumentParser(description="Generate item markdown from script/csv/items.csv (Gemini).")
    parser.add_argument(
        "--enrich-trust",
        action="store_true",
        help="Only refresh maps_url + editorial/illustration notes on existing item *.md (no Gemini).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Max rows from items.csv (0 or negative = all rows). If omitted, uses env CONTENT_LIMIT, else all rows.",
    )
    args = parser.parse_args()
    if args.enrich_trust:
        enrich_trust_metadata_all_items()
        return
    if args.limit is not None:
        lim = args.limit
    else:
        raw = os.environ.get("CONTENT_LIMIT", "").strip()
        if not raw:
            lim = 0
        else:
            try:
                lim = int(raw)
            except ValueError:
                lim = 0
    run_generator(limit=lim)


if __name__ == "__main__":
    _parse_cli_and_run()
