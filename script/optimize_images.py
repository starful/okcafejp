"""
OK Series shared image optimizer.
- Resizes and compresses images under `app/static/images/`.
"""
import os
from PIL import Image

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR   = os.path.dirname(SCRIPT_DIR)
IMAGES_DIR = os.path.join(BASE_DIR, 'app', 'static', 'images')

MAX_WIDTH  = 1200
MAX_HEIGHT = 800
QUALITY    = 82  # 0-95, 82 is a practical quality/size balance


def optimize(filepath: str):
    try:
        with Image.open(filepath) as img:
            original_size = os.path.getsize(filepath)

            # RGBA -> RGB conversion (JPEG has no alpha channel)
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')

            # Resize while preserving aspect ratio
            img.thumbnail((MAX_WIDTH, MAX_HEIGHT), Image.LANCZOS)

            img.save(filepath, 'JPEG', quality=QUALITY, optimize=True)
            new_size = os.path.getsize(filepath)
            saved_kb = (original_size - new_size) // 1024
            print(f"✅ {os.path.basename(filepath)}: {original_size//1024}KB -> {new_size//1024}KB (saved {saved_kb}KB)")
    except Exception as e:
        print(f"❌ {os.path.basename(filepath)}: {e}")


def run():
    if not os.path.exists(IMAGES_DIR):
        print("❌ images directory not found")
        return

    targets = [
        os.path.join(IMAGES_DIR, f)
        for f in os.listdir(IMAGES_DIR)
        if f.lower().endswith(('.jpg', '.jpeg', '.png'))
        and not f.startswith('logo')
        and not f.startswith('favicon')
    ]

    if not targets:
        print("No images to optimize")
        return

    print(f"🖼️  Starting optimization for {len(targets)} images...")
    for path in targets:
        optimize(path)
    print("🎉 Image optimization complete")


if __name__ == "__main__":
    run()
