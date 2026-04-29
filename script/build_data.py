"""
OK Series shared data builder.
- Reads `app/content/*.md` and builds `app/static/json/items_data.json`.
- Called from Dockerfile via `RUN python script/build_data.py`.
"""
import os
import json
import re
import importlib.util
import frontmatter
from datetime import datetime

BASE_DIR    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTENT_DIR = os.path.join(BASE_DIR, 'app', 'content')
OUTPUT_PATH = os.path.join(BASE_DIR, 'app', 'static', 'json', 'items_data.json')

def _load_data_key() -> str:
    config_path = os.path.join(BASE_DIR, "app", "config.py")
    default_key = "items"

    if not os.path.exists(config_path):
        return default_key

    try:
        spec = importlib.util.spec_from_file_location("oktemplate_config", config_path)
        if spec is None or spec.loader is None:
            return default_key
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        site_config = getattr(module, "SITE_CONFIG", {})
        return str(site_config.get("data_key", default_key))
    except Exception:
        return default_key


def clean_md(text: str) -> str:
    text = text.strip()
    text = re.sub(r'^```[a-z]*\n', '', text)
    text = re.sub(r'\n```$', '', text)
    text = re.sub(r'^(##\s*)?yaml\n', '', text, flags=re.IGNORECASE)
    if '---' in text and not text.startswith('---'):
        text = '---' + text.split('---', 1)[1]
    return text


def main():
    print("🔨 Building items_data.json ...")
    items = []
    data_key = _load_data_key()

    if not os.path.exists(CONTENT_DIR):
        print("❌ content directory not found")
        return

    for filename in os.listdir(CONTENT_DIR):
        if not filename.endswith('.md'):
            continue

        fpath = os.path.join(CONTENT_DIR, filename)
        try:
            with open(fpath, 'r', encoding='utf-8') as f:
                raw = f.read()

            post = frontmatter.loads(clean_md(raw))

            # Normalize categories
            cats = post.get('categories', [])
            if isinstance(cats, str):
                cats = [c.strip() for c in cats.split(',')]

            # Fallback summary
            summary = str(post.get('summary', ''))
            if not summary or len(summary) < 10:
                clean_body = re.sub(r'[#*`\-]', '', post.content).strip()
                summary = clean_body[:180].replace('\n', ' ') + '...'

            # Safe lat/lng parsing
            try:
                lat = float(post.get('lat') or 0)
                lng = float(post.get('lng') or 0)
            except (ValueError, TypeError):
                lat, lng = 0.0, 0.0

            if lat == 0.0 or lng == 0.0:
                print(f"⚠️  Skip {filename}: missing lat/lng")
                continue

            item_id = filename.replace('.md', '')
            items.append({
                "id":          item_id,
                "lang":        str(post.get('lang', 'en')),
                "title":       str(post.get('title', 'Untitled')),
                "lat":         lat,
                "lng":         lng,
                "categories":  cats,
                "thumbnail":   str(post.get('thumbnail', '/static/images/default.jpg')),
                "address":     str(post.get('address', 'Japan')),
                "published":   str(post.get('date', datetime.now().strftime('%Y-%m-%d'))),
                "summary":     summary,
                "agoda":       str(post.get('agoda', '')),
                "link":        f"/item/{item_id}",
            })
        except Exception as e:
            print(f"❌ Skip {filename}: {e}")

    items.sort(key=lambda x: x['published'], reverse=True)

    output = {
        "last_updated": datetime.now().strftime("%Y.%m.%d"),
        "total_count":  len(items),
        data_key:       items,
    }

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"🎉 Done: {len(items)} items -> items_data.json")


if __name__ == "__main__":
    main()
