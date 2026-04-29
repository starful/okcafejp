import os

# ============================================================
#  ✅ OK Series core config
#  For a new project, this is the main file to edit.
# ============================================================

SITE_CONFIG = {

    # ----------------------------------------------------------
    # 1. Basic identity
    # ----------------------------------------------------------
    "project_name":  "oktemplate",          # GCS prefix / Cloud Run service name
    "site_name":     "OKTemplate",          # Display name (e.g. OKRamen, OKOnsen)
    "site_url":      os.getenv("SITE_URL", "https://oktemplate.net"),
    "tagline":       "Discover the Best of Japan",
    "data_key":      "items",               # Top-level JSON key (items/courses/etc.)

    # ----------------------------------------------------------
    # 2. SEO / analytics
    # ----------------------------------------------------------
    "ga_id":         os.getenv("GA_ID", "G-XXXXXXXXXX"),    # Google Analytics ID
    "maps_api_key":  os.getenv("MAPS_API_KEY", ""),         # Google Maps JS API Key
    "maps_id":       os.getenv("MAPS_ID", ""),              # Google Cloud Maps ID (Advanced Markers)

    # ----------------------------------------------------------
    # 3. Icon & theme
    # ----------------------------------------------------------
    "emoji":         "🗾",                   # Site emoji for header/footer
    "accent_color":  "#e74c3c",             # CSS accent color
    "bg_dot_color":  "#f39c12",             # Background dot color

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
        "https://images.unsplash.com/photo-1552611052-33e04de081de?q=80&w=800&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1569718212165-3a8278d5f624?q=80&w=800&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1555126634-323283e090fa?q=80&w=800&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1511910849309-0dffb8785146?q=80&w=800&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1534604973900-c43ab4c2e0ab?q=80&w=800&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1526318896980-cf78c088247c?q=80&w=800&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1503764654157-72d979d9af2f?q=80&w=800&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1455619452474-d2be8b1e70cd?q=80&w=800&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1553621042-f6e147245754?q=80&w=800&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1467003909585-2f8a72700288?q=80&w=800&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1506368249639-73a05d6f6488?q=80&w=800&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1525755662778-989d0524087e?q=80&w=800&auto=format&fit=crop",
        "https://images.unsplash.com/photo-1591814441348-73546747d96a?q=80&w=800&auto=format&fit=crop",
    ],

    # ----------------------------------------------------------
    # 9. Footer
    # ----------------------------------------------------------
    "footer_tagline":  "Curating the best of Japan.",
    "footer_year":     "2026",
}
