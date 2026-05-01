# OKCafeJP

Map-driven Japan cafe discovery platform for EN/KO travelers, built on the OK Series stack.

## Project Structure

```text
okcafejp/
├── app/
│   ├── __init__.py
│   ├── config.py
│   ├── content/
│   │   └── guides/
│   ├── static/
│   │   ├── css/style.css
│   │   ├── js/
│   │   ├── json/items_data.json
│   │   └── site.webmanifest
│   └── templates/
├── script/
│   ├── item_generator.py
│   ├── guide_generator.py
│   ├── build_data.py
│   ├── fetch_images.py
│   ├── fetch_items_from_places.py
│   ├── optimize_images.py
│   ├── quickstart.py
│   └── csv/
│       ├── items.csv
│       └── guides.csv
├── cloudbuild.yaml
├── deploy.sh
└── .env.example
```

## Quick Start

1. Fill starter data:
   - `script/csv/items.csv`
   - `script/csv/guides.csv`
2. Generate starter markdown and JSON:

```bash
python script/quickstart.py
```

3. Run locally:

```bash
python run.py
```

Open `http://localhost:8080`.

## Populate `items.csv` from Google Places

Use seed **Lat**, **Lng**, and **Address** (neighbourhood hint) from `script/csv/items.csv` (the `Name` column is ignored). The script calls **Places API (New)** and writes **real business names**, coordinates, and `formattedAddress` from Google.

1. In [Google Cloud Console](https://console.cloud.google.com/), enable **Places API (New)** for the project that owns the key.
2. Set `GOOGLE_PLACES_API_KEY` in `.env`.
3. Run (writes `script/csv/items_from_places.csv` by default):

```bash
python script/fetch_items_from_places.py --input script/csv/items.csv
```

Overwrite `items.csv` after reviewing the output (a backup is created next to the file):

```bash
python script/fetch_items_from_places.py --input script/csv/items.csv --in-place
```

Then regenerate site data: `python script/build_data.py` (and item markdown if you use the generator).

## New Project Setup

1. Copy template:

```bash
cp -r okcafejp your-project-name
cd your-project-name
```

2. Update `app/config.py`:
   - `project_name`
   - `site_name`
   - `site_url`
   - `tagline`
   - category mapping/theme values

3. Update CSV inputs:
   - `script/csv/items.csv` (`Name,Lat,Lng,Address,Features,Agoda`)
   - `script/csv/guides.csv` (`id,topic_en,topic_ko,keywords`)

4. Check deploy settings:
   - `cloudbuild.yaml` substitutions and secret names
   - optional env overrides in `deploy.sh`

## Deployment

Default full flow:

```bash
chmod +x deploy.sh
./deploy.sh
```

Optional modes:

```bash
./deploy.sh --content-only
./deploy.sh --content-only --with-git --with-deploy
./deploy.sh --deploy-only
```

## Environment Variables

Copy `.env.example` to `.env`:

```env
GEMINI_API_KEY=your_key
GOOGLE_PLACES_API_KEY=your_key
MAPS_API_KEY=your_maps_js_key
SITE_URL=https://your-domain.net
ASSET_VERSION=2026-04-29
```
