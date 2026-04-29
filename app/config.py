import os

# ============================================================
#  ✅ OK Series core config
#  For a new project, this is the main file to edit.
# ============================================================

SITE_CONFIG = {

    # ----------------------------------------------------------
    # 1. Basic identity
    # ----------------------------------------------------------
    "project_name":  "okcafejp",            # GCS prefix / Cloud Run service name
    "site_name":     "OKCafeJP",            # Display name (e.g. OKRamen, OKOnsen)
    "site_url":      os.getenv("SITE_URL", "https://okcafejp.net"),
    "tagline":       "Discover Japan's Best Cafes for Travelers",
    "data_key":      "items",               # Top-level JSON key (items/courses/etc.)

    # ----------------------------------------------------------
    # 2. SEO / analytics
    # ----------------------------------------------------------
    "ga_id":         os.getenv("GA_ID", "G-P2PSDNKE9D"),    # Google Analytics 4 (gtag)
    "maps_api_key":  os.getenv("MAPS_API_KEY", ""),         # Google Maps JS API Key
    "maps_id":       os.getenv("MAPS_ID", ""),              # Google Cloud Maps ID (Advanced Markers)

    # ----------------------------------------------------------
    # 3. Icon & theme
    # ----------------------------------------------------------
    "emoji":         "☕",                   # Site emoji for header/footer
    "accent_color":  "#8b5e3c",             # CSS accent color
    "bg_dot_color":  "#d6b48a",             # Background dot color

    # ----------------------------------------------------------
    # 4. Header filter buttons
    #    { "label": "Button text", "theme": "JS filter key", "count_id": "HTML id" }
    # ----------------------------------------------------------
    "filter_buttons": [
        {"label": "All",           "theme": "all",      "count_id": "count-all"},
        {"label": "☕ Specialty",   "theme": "specialty", "count_id": "count-specialty"},
        {"label": "🍰 Dessert",     "theme": "dessert",   "count_id": "count-dessert"},
        {"label": "💻 Work-Friendly","theme": "work",      "count_id": "count-work"},
        {"label": "🌿 Scenic",      "theme": "scenic",    "count_id": "count-scenic"},
    ],

    # ----------------------------------------------------------
    # 5. Category mapping (source -> UI label)
    # ----------------------------------------------------------
    "category_mapping": {
        "Specialty": "Specialty",
        "Dessert": "Dessert",
        "Work-Friendly": "Work-Friendly",
        "Scenic": "Scenic",
        "Vintage": "Vintage",
        "Roastery": "Roastery",
    },

    # ----------------------------------------------------------
    # 6. JS category map (used by main.js)
    #    { "theme_key": "display_name" }
    # ----------------------------------------------------------
    "js_category_map": {
        "specialty": "Specialty",
        "dessert": "Dessert",
        "work": "Work-Friendly",
        "scenic": "Scenic",
        "vintage": "Vintage",
        "roastery": "Roastery",
    },

    # ----------------------------------------------------------
    # 7. Detail page schema type (JSON-LD)
    # ----------------------------------------------------------
    "schema_type": "Restaurant",

    # ----------------------------------------------------------
    # 8. Guide section images
    # ----------------------------------------------------------
    "guide_images": [
        # Dedicated guide image pool (separate from item thumbnails)
        "/static/images/guides/guide_cover_01.jpg",
        "/static/images/guides/guide_cover_02.jpg",
        "/static/images/guides/guide_cover_03.jpg",
        "/static/images/guides/guide_cover_04.jpg",
        "/static/images/guides/guide_cover_05.jpg",
        "/static/images/guides/guide_cover_06.jpg",
        "/static/images/guides/guide_cover_07.jpg",
        "/static/images/guides/guide_cover_08.jpg",
        "/static/images/guides/guide_cover_09.jpg",
        "/static/images/guides/guide_cover_10.jpg",
    ],

    # ----------------------------------------------------------
    # 9. Footer
    # ----------------------------------------------------------
    "footer_tagline":  "Curating the best cafes in Japan for EN/KO travelers.",
    "footer_year":     "2026",
}
