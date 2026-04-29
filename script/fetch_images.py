"""
OK Series shared image generator (Vertex Imagen — okramen 과 동일 경로).
- Reads `image_prompt` from content markdown files.
- Saves generated images to `app/static/images/`.
"""
import os
import re
import frontmatter
from dotenv import load_dotenv

load_dotenv()

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SCRIPT_DIR)
CONTENT_DIR = os.path.join(BASE_DIR, "app", "content")
IMAGES_DIR = os.path.join(BASE_DIR, "app", "static", "images")

# okramen/script/generate_images.py 와 동일: Vertex + Imagen 4 Fast
GCP_PROJECT = os.environ.get("GCP_PROJECT", "starful-258005")
GCP_LOCATION = os.environ.get("GCP_LOCATION", "us-central1")
IMAGEN_MODEL = os.environ.get("IMAGEN_MODEL", "imagen-4.0-fast-generate-001")
# Cafe 프롬프트에 인물·바리스타 등이 묵시될 수 있어 okramen 식 DONT_ALLOW 는 전부 RAI 차단될 수 있음
IMAGEN_PERSON_GEN = os.environ.get("IMAGEN_PERSON_GENERATION", "ALLOW_ADULT")


def clean_md(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```[a-z]*\n", "", text)
    text = re.sub(r"\n```$", "", text)
    if "---" in text and not text.startswith("---"):
        text = "---" + text.split("---", 1)[1]
    return text.strip()


def generate_image(safe_name: str, prompt: str) -> bool:
    out_path = os.path.join(IMAGES_DIR, f"{safe_name}.jpg")
    if os.path.exists(out_path) and os.path.getsize(out_path) > 1024:
        print(f"⏭️  Skip (already exists): {safe_name}.jpg")
        return True
    if os.path.exists(out_path) and os.path.getsize(out_path) <= 1024:
        try:
            os.remove(out_path)
        except OSError:
            pass

    try:
        from google import genai
        from google.genai import types
    except ImportError:
        print("❌ google-genai package missing: pip install google-genai")
        return False

    suffix = (
        "Photorealistic editorial travel photography, natural light, "
        "cozy cafe atmosphere, shallow depth of field, no text, no watermark, professional quality."
    )
    attempts: list[tuple[str, str]] = [
        (f"{prompt}. {suffix}", IMAGEN_PERSON_GEN),
        (
            f"{prompt}. Wide quiet cafe interior, empty seating or very distant figures, no minors. {suffix}",
            "ALLOW_ALL",
        ),
    ]

    try:
        client = genai.Client(
            vertexai=True,
            project=GCP_PROJECT,
            location=GCP_LOCATION,
        )
        for attempt_i, (enhanced, person_gen) in enumerate(attempts):
            response = client.models.generate_images(
                model=IMAGEN_MODEL,
                prompt=enhanced,
                config=types.GenerateImagesConfig(
                    number_of_images=1,
                    aspect_ratio="16:9",
                    output_mime_type="image/jpeg",
                    person_generation=person_gen,
                ),
            )
            if not response.generated_images:
                print(f"❌ No image in response ({safe_name})")
                return False
            gi = response.generated_images[0]
            if gi.rai_filtered_reason:
                if attempt_i + 1 < len(attempts):
                    print(f"⚠️  RAI retry ({safe_name}): {gi.rai_filtered_reason[:80]}...")
                    continue
                print(f"❌ RAI filtered ({safe_name}): {gi.rai_filtered_reason}")
                return False
            img_obj = gi.image
            if img_obj is None:
                print(f"❌ No image payload ({safe_name})")
                return False
            img_bytes = img_obj.image_bytes
            if not img_bytes and img_obj.gcs_uri:
                print(f"❌ Image only as GCS URI ({safe_name}): {img_obj.gcs_uri}")
                return False
            if not img_bytes:
                print(f"❌ Empty image bytes ({safe_name})")
                return False
            os.makedirs(IMAGES_DIR, exist_ok=True)
            with open(out_path, "wb") as f:
                f.write(img_bytes)
            print(f"✅ Image generated: {safe_name}.jpg ({len(img_bytes) // 1024}KB)")
            return True
    except Exception as e:
        print(f"❌ Image generation failed ({safe_name}): {e}")
        return False


def run():
    print(f"🖼️  Imagen via Vertex: project={GCP_PROJECT} region={GCP_LOCATION} model={IMAGEN_MODEL}")

    if not os.path.isdir(CONTENT_DIR):
        print("❌ content directory not found")
        return

    processed = set()
    for filename in sorted(os.listdir(CONTENT_DIR)):
        if not filename.endswith("_en.md"):
            continue
        safe_name = filename.replace("_en.md", "")
        if safe_name in processed:
            continue

        fpath = os.path.join(CONTENT_DIR, filename)
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                post = frontmatter.loads(clean_md(f.read()))
            prompt = str(post.get("image_prompt", ""))
            if not prompt or len(prompt) < 10:
                print(f"⚠️  image_prompt is missing: {filename}")
                continue
            generate_image(safe_name, prompt)
            processed.add(safe_name)
        except Exception as e:
            print(f"❌ Failed to read file ({filename}): {e}")


if __name__ == "__main__":
    run()
