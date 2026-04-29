"""
OK Series shared image generator (Google Imagen 3).
- Reads `image_prompt` from content markdown files.
- Saves generated images to `app/static/images/`.
"""
import os
import re
import base64
import frontmatter
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.environ.get("GEMINI_API_KEY")

SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
BASE_DIR    = os.path.dirname(SCRIPT_DIR)
CONTENT_DIR = os.path.join(BASE_DIR, 'app', 'content')
IMAGES_DIR  = os.path.join(BASE_DIR, 'app', 'static', 'images')


def clean_md(text: str) -> str:
    text = text.strip()
    text = re.sub(r'^```[a-z]*\n', '', text)
    text = re.sub(r'\n```$', '', text)
    if '---' in text and not text.startswith('---'):
        text = '---' + text.split('---', 1)[1]
    return text


def generate_image(safe_name: str, prompt: str):
    out_path = os.path.join(IMAGES_DIR, f"{safe_name}.jpg")
    if os.path.exists(out_path):
        print(f"⏭️  Skip (already exists): {safe_name}.jpg")
        return

    try:
        from google import genai
        from google.genai import types
        client = genai.Client(api_key=API_KEY)
        response = client.models.generate_images(
            model='imagen-3.0-generate-002',
            prompt=prompt,
            config=types.GenerateImagesConfig(
                number_of_images=1,
                aspect_ratio='16:9',
                output_mime_type='image/jpeg',
            )
        )
        img_bytes = base64.b64decode(response.generated_images[0].image.image_bytes)
        os.makedirs(IMAGES_DIR, exist_ok=True)
        with open(out_path, 'wb') as f:
            f.write(img_bytes)
        print(f"✅ Image generated: {safe_name}.jpg")
    except Exception as e:
        print(f"❌ Image generation failed ({safe_name}): {e}")


def run():
    if not API_KEY:
        print("❌ GEMINI_API_KEY is missing")
        return

    processed = set()
    for filename in os.listdir(CONTENT_DIR):
        if not filename.endswith('_en.md'):  # generate once per EN source file
            continue
        safe_name = filename.replace('_en.md', '')
        if safe_name in processed:
            continue

        fpath = os.path.join(CONTENT_DIR, filename)
        try:
            with open(fpath, 'r', encoding='utf-8') as f:
                post = frontmatter.loads(clean_md(f.read()))
            prompt = str(post.get('image_prompt', ''))
            if not prompt or len(prompt) < 10:
                print(f"⚠️  image_prompt is missing: {filename}")
                continue
            generate_image(safe_name, prompt)
            processed.add(safe_name)
        except Exception as e:
            print(f"❌ Failed to read file ({filename}): {e}")


if __name__ == "__main__":
    run()
