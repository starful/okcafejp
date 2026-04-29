"""
OK Series shared guide content generator.
- Generates EN/KO guide markdown files from guides.csv topics.
"""
import os
import csv
import re
import time
import concurrent.futures
from datetime import datetime
from dotenv import load_dotenv

from item_generator import guide_stem_from_topic_en, uniquify_slugs

load_dotenv()
API_KEY = os.environ.get("GEMINI_API_KEY")

# okramen guide / okcaddie 와 동일 계열 Flash (유료 키 장문 생성)
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
GUIDE_MAX_WORKERS = int(os.environ.get("GEMINI_GUIDE_MAX_WORKERS", "3"))

SCRIPT_DIR      = os.path.dirname(os.path.abspath(__file__))
BASE_DIR        = os.path.dirname(SCRIPT_DIR)
GUIDE_DIR       = os.path.join(BASE_DIR, 'app', 'content', 'guides')


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
    text = re.sub(r'^```[a-z]*\n', '', text)
    text = re.sub(r'\n```$', '', text)
    text = re.sub(r'^(##\s*)?yaml\n', '', text, flags=re.IGNORECASE)
    if '---' in text and not text.startswith('---'):
        text = '---' + text.split('---', 1)[1]
    return text.strip()


def generate_guide(guide_id: str, topic: str, lang: str, keywords: str):
    if not API_KEY:
        print("❌ GEMINI_API_KEY is missing")
        return

    try:
        from google import genai
        client = genai.Client(api_key=API_KEY)
    except ImportError:
        print("❌ google-genai package required: pip install google-genai")
        return

    print(f"🚀 [Guide AI] Generating {guide_id}_{lang}.md ...")

    prompt = f"""
You are a professional travel blogger and Japan expert.
Write a high-quality, SEO-optimized educational guide article.

[Topic]
- Subject: {topic}
- Language: {lang}
- SEO Keywords: {keywords}

[Output Format - STRICT]
---
lang: {lang}
title: "Write a catchy, SEO-friendly title in {'Korean' if lang == 'ko' else 'English'}"
date: "{datetime.now().strftime('%Y-%m-%d')}"
summary: "Write a compelling 2-sentence summary on a single line."
---

[Article Requirements]
1. Introduction: Hook the reader immediately.
2. Main Content: Use descriptive H2 and H3 headers. Bold key terms.
3. Bullet points and numbered lists where helpful.
4. Keep the article body between 7,000 and 8,000 characters for SEO depth.
5. Conclusion: Call to action — encourage readers to use the interactive map.

IMPORTANT: Do NOT use markdown code blocks (```). Start directly with '---'.
"""

    try:
        final_text = ""
        for _ in range(5):
            response = _generate_content_with_retry(client, GEMINI_MODEL, prompt)
            final_text = clean_ai_response(response.text)
            if len(final_text) >= 7000:
                break
        if len(final_text) < 7000:
            print(f"❌ [Failed] {guide_id} ({lang}): too short ({len(final_text)} chars)")
            return
        os.makedirs(GUIDE_DIR, exist_ok=True)
        filename = f"{guide_id}_{lang}.md"
        with open(os.path.join(GUIDE_DIR, filename), 'w', encoding='utf-8') as f:
            f.write(final_text)
        print(f"✅ [Done] {filename} ({len(final_text):,} chars)")
    except Exception as e:
        print(f"❌ [Failed] {guide_id} ({lang}): {e}")


def run_guide_generator(limit: int = 3):
    csv_path = os.path.join(SCRIPT_DIR, 'csv', 'guides.csv')
    if not os.path.exists(csv_path):
        print(f"❌ CSV not found: {csv_path}")
        return

    tasks = []
    batch_rows: list[dict] = []
    with open(csv_path, mode='r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if len(batch_rows) >= limit:
                break
            batch_rows.append(row)

    stems_raw = [guide_stem_from_topic_en((r.get("topic_en") or "").strip()) for r in batch_rows]
    guide_stems = uniquify_slugs(stems_raw)

    for row, guide_id in zip(batch_rows, guide_stems):
        keywords = row.get('keywords', '').strip()

        en_path = os.path.join(GUIDE_DIR, f"{guide_id}_en.md")
        ko_path = os.path.join(GUIDE_DIR, f"{guide_id}_ko.md")

        if not os.path.exists(en_path):
            tasks.append((guide_id, row['topic_en'], 'en', keywords))
        if not os.path.exists(ko_path):
            tasks.append((guide_id, row['topic_ko'], 'ko', keywords))

    if not tasks:
        print("✨ No new guides to generate.")
        return

    print(
        f"🔔 Starting generation for {len(tasks)} guide files "
        f"(model={GEMINI_MODEL}, workers={GUIDE_MAX_WORKERS}, 429 retry)..."
    )
    with concurrent.futures.ThreadPoolExecutor(max_workers=GUIDE_MAX_WORKERS) as ex:
        ex.map(lambda p: generate_guide(*p), tasks)


if __name__ == "__main__":
    run_guide_generator(limit=3)
