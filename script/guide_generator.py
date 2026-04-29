"""
OK Series shared guide content generator.
- Generates EN/KO guide markdown files from guides.csv topics.
"""
import os
import csv
import re
import concurrent.futures
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.environ.get("GEMINI_API_KEY")

SCRIPT_DIR      = os.path.dirname(os.path.abspath(__file__))
BASE_DIR        = os.path.dirname(SCRIPT_DIR)
GUIDE_DIR       = os.path.join(BASE_DIR, 'app', 'content', 'guides')


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

    print(f"🚀 [Guide AI] Generating {lang} guide: {topic}...")

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
4. Minimum 4,000 characters for SEO depth.
5. Conclusion: Call to action — encourage readers to use the interactive map.

IMPORTANT: Do NOT use markdown code blocks (```). Start directly with '---'.
"""

    try:
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=prompt
        )
        final_text = clean_ai_response(response.text)
        os.makedirs(GUIDE_DIR, exist_ok=True)
        filename = f"{guide_id}_{lang}.md"
        with open(os.path.join(GUIDE_DIR, filename), 'w', encoding='utf-8') as f:
            f.write(final_text)
        print(f"✅ [Done] {filename}")
    except Exception as e:
        print(f"❌ [Failed] {guide_id} ({lang}): {e}")


def run_guide_generator(limit: int = 3):
    csv_path = os.path.join(SCRIPT_DIR, 'csv', 'guides.csv')
    if not os.path.exists(csv_path):
        print(f"❌ CSV not found: {csv_path}")
        return

    tasks = []
    created = 0

    with open(csv_path, mode='r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            guide_id = row['id'].strip()
            keywords = row.get('keywords', '').strip()

            en_path = os.path.join(GUIDE_DIR, f"{guide_id}_en.md")
            ko_path = os.path.join(GUIDE_DIR, f"{guide_id}_ko.md")

            if not os.path.exists(en_path):
                tasks.append((guide_id, row['topic_en'], 'en', keywords))
            if not os.path.exists(ko_path):
                tasks.append((guide_id, row['topic_ko'], 'ko', keywords))

            if not os.path.exists(en_path) or not os.path.exists(ko_path):
                created += 1

            if created >= limit:
                break

    if not tasks:
        print("✨ No new guides to generate.")
        return

    print(f"🔔 Starting generation for {len(tasks)} guide files...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as ex:
        ex.map(lambda p: generate_guide(*p), tasks)


if __name__ == "__main__":
    run_guide_generator(limit=3)
