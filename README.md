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
