from flask import Flask, jsonify, render_template, abort, redirect, request, Response, send_from_directory
from flask_compress import Compress
import json, os, frontmatter, markdown, re, glob, hashlib, copy, urllib.parse
from datetime import datetime

app = Flask(__name__)
Compress(app)

# ==========================================
# ✅ Config import (main customization point)
# ==========================================
try:
    from .config import SITE_CONFIG
except ImportError:
    from config import SITE_CONFIG

# ==========================================
# Paths
# ==========================================
BASE_DIR    = app.root_path
STATIC_DIR  = os.path.join(BASE_DIR, 'static')
DATA_FILE   = os.path.join(STATIC_DIR, 'json', 'items_data.json')
CONTENT_DIR = os.path.join(BASE_DIR, 'content')
GUIDE_DIR   = os.path.join(CONTENT_DIR, 'guides')

# ==========================================
# Image mapping helpers
# ==========================================
GUIDE_IMAGES = SITE_CONFIG['guide_images']

def get_mapped_image(base_id):
    idx = int(hashlib.md5(base_id.encode()).hexdigest(), 16) % len(GUIDE_IMAGES)
    return GUIDE_IMAGES[idx]

# ==========================================
# Data loading (startup cache)
# ==========================================
CACHED_DATA   = {SITE_CONFIG['data_key']: [], "last_updated": ""}
CACHED_GUIDES = {'en': [], 'ko': []}

def load_items():
    global CACHED_DATA
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                CACHED_DATA = json.load(f)
            print(f"✅ Data loaded: {len(CACHED_DATA.get(SITE_CONFIG['data_key'], []))} items")
        except Exception as e:
            print(f"❌ Data load error: {e}")

def load_guides():
    global CACHED_GUIDES
    if not os.path.exists(GUIDE_DIR):
        return

    all_raw = []
    for fpath in glob.glob(os.path.join(GUIDE_DIR, '*.md')):
        try:
            with open(fpath, 'r', encoding='utf-8') as f:
                raw = f.read().strip()
            raw = _clean_md(raw)
            post    = frontmatter.loads(raw)
            lang    = 'ko' if '_ko.md' in fpath else 'en'
            base_id = os.path.basename(fpath).rsplit('_', 1)[0]
            full_id = os.path.basename(fpath).replace('.md', '')
            all_raw.append({
                'base_id': base_id, 'lang': lang, 'full_id': full_id,
                'title':   str(post.get('title', 'Guide')),
                'summary': str(post.get('summary', '')),
                'date':    str(post.get('date', '2026-01-01'))
            })
        except:
            continue

    # Sort by date and assign image indexes (avoid consecutive duplicates)
    ref_en = sorted([g for g in all_raw if g['lang'] == 'en'], key=lambda x: x['date'], reverse=True)
    last_idx = -1
    id_to_img = {}
    for g in ref_en:
        idx = int(hashlib.md5(g['base_id'].encode()).hexdigest(), 16) % len(GUIDE_IMAGES)
        if idx == last_idx:
            idx = (idx + 1) % len(GUIDE_IMAGES)
        id_to_img[g['base_id']] = GUIDE_IMAGES[idx]
        last_idx = idx

    new_guides = {'en': [], 'ko': []}
    for g in all_raw:
        new_guides[g['lang']].append({
            'id':        g['full_id'],
            'title':     g['title'],
            'summary':   g['summary'],
            'thumbnail': id_to_img.get(g['base_id'], GUIDE_IMAGES[0]),
            'published': g['date']
        })
    for lang in ['en', 'ko']:
        new_guides[lang].sort(key=lambda x: x['published'], reverse=True)

    CACHED_GUIDES = new_guides
    total = sum(len(v) for v in new_guides.values())
    print(f"✅ Guides loaded: {total}")

def _clean_md(text):
    """Clean common AI output artifacts from markdown."""
    text = re.sub(r'^```[a-z]*\n', '', text)
    text = re.sub(r'\n```$', '', text)
    text = re.sub(r'^(##\s*)?yaml\n', '', text, flags=re.IGNORECASE)
    if '---' in text and not text.startswith('---'):
        text = '---' + text.split('---', 1)[1]
    return text.strip()

def _get_footer_stats(lang):
    items = CACHED_DATA.get(SITE_CONFIG['data_key'], [])
    count = len([i for i in items if i.get('lang') == lang])
    return {
        'total_items':   count if count > 0 else len(items) // 2,
        'last_updated':  CACHED_DATA.get('last_updated', ''),
        'site':          SITE_CONFIG
    }


def _absolute_url(path_or_url):
    if not path_or_url:
        return ""
    if path_or_url.startswith("http://") or path_or_url.startswith("https://"):
        return path_or_url
    return f"{SITE_CONFIG['site_url'].rstrip('/')}/{path_or_url.lstrip('/')}"

# Initial startup load
load_items()
load_guides()

# ==========================================
# Category mapping
# ==========================================
CATEGORY_MAPPING = SITE_CONFIG.get('category_mapping', {})

# ==========================================
# Routes
# ==========================================
@app.route('/')
def index():
    lang = request.args.get('lang', 'en')
    items = CACHED_DATA.get(SITE_CONFIG['data_key'], [])
    initial_items = [i for i in items if i.get('lang') == lang]
    if not initial_items:
        initial_items = [i for i in items if i.get('lang') == 'en']
    initial_items = initial_items[:24]
    top_guides = CACHED_GUIDES.get(lang, [])[:3]
    stats = _get_footer_stats(lang)
    canonical = SITE_CONFIG['site_url'] if lang == 'en' else f"{SITE_CONFIG['site_url']}?lang={lang}"
    return render_template('index.html', lang=lang, guides=CACHED_GUIDES,
                           top_guides=top_guides, initial_items=initial_items,
                           canonical=canonical, **stats)

@app.route('/api/items')
def api_items():
    lang = request.args.get('lang', 'en')
    items = CACHED_DATA.get(SITE_CONFIG['data_key'], [])
    filtered = [i for i in items if i.get('lang') == lang]
    if not filtered:
        filtered = [i for i in items if i.get('lang') == 'en']

    spoofed = []
    for item in filtered:
        s = copy.deepcopy(item)
        s['lang'] = lang
        new_cats = [CATEGORY_MAPPING.get(c.strip(), c.strip()) for c in s.get('categories', [])]
        s['categories'] = list(set(new_cats))
        spoofed.append(s)

    return jsonify({SITE_CONFIG['data_key']: spoofed, "last_updated": CACHED_DATA.get('last_updated')})

@app.route('/guide')
def guide_list():
    lang = request.args.get('lang', 'en')
    stats = _get_footer_stats(lang)
    canonical = f"{SITE_CONFIG['site_url']}/guide" if lang == 'en' else f"{SITE_CONFIG['site_url']}/guide?lang={lang}"
    return render_template('guide_list.html', guides=CACHED_GUIDES, lang=lang, canonical=canonical, **stats)

@app.route('/guide/<guide_id>')
def guide_detail(guide_id):
    path = os.path.join(GUIDE_DIR, f"{guide_id}.md")
    if not os.path.exists(path):
        return redirect('/guide')

    with open(path, 'r', encoding='utf-8') as f:
        raw = _clean_md(f.read())
    post  = frontmatter.loads(raw)
    body  = re.sub(r'---.*?---', '', post.content, flags=re.DOTALL)
    body  = body.replace('```markdown', '').replace('```', '').strip()

    title   = str(post.get('title') or guide_id)
    lang    = str(post.get('lang', 'en'))
    base_id = guide_id.rsplit('_', 1)[0]
    image   = get_mapped_image(base_id)
    stats   = _get_footer_stats(lang)
    alt_en = f"{SITE_CONFIG['site_url']}/guide/{base_id}_en"
    alt_ko = f"{SITE_CONFIG['site_url']}/guide/{base_id}_ko"

    content_html = markdown.markdown(body, extensions=['tables', 'toc', 'fenced_code'])
    return render_template('guide_detail.html',
                           title=title, content=content_html, lang=lang,
                           guide_id=guide_id, base_id=base_id,
                           image_url=image, image_url_abs=_absolute_url(image),
                           canonical=f"{SITE_CONFIG['site_url']}/guide/{guide_id}",
                           alt_en=alt_en, alt_ko=alt_ko, post=post, **stats)

@app.route('/item/<item_id>')
def item_detail(item_id):
    md_path = os.path.join(CONTENT_DIR, f"{item_id}.md")
    if not os.path.exists(md_path):
        abort(404)

    with open(md_path, 'r', encoding='utf-8') as f:
        raw = _clean_md(f.read())
    post = frontmatter.loads(raw)
    post['id'] = item_id

    if isinstance(post.get('categories'), str):
        post['categories'] = [c.strip() for c in post['categories'].split(',')]

    content_html = markdown.markdown(post.content, extensions=['tables', 'fenced_code'])
    lang  = str(post.get('lang', 'en'))
    stats = _get_footer_stats(lang)
    return render_template(
        'detail.html',
        post=post,
        content=content_html,
        thumbnail_abs=_absolute_url(str(post.get('thumbnail', '/static/images/default.jpg'))),
        **stats
    )

# Static assets / SEO
@app.route('/static/images/<path:filename>')
def serve_images(filename):
    image_dir = os.path.join(STATIC_DIR, 'images')
    local_path = os.path.join(image_dir, filename)
    # Prefer local files (important for local preview and freshly generated images).
    if os.path.exists(local_path):
        return send_from_directory(image_dir, filename)
    project_name = SITE_CONFIG['project_name']
    version = os.environ.get('ASSET_VERSION', '').strip()
    url = f"https://storage.googleapis.com/ok-project-assets/{project_name}/{filename}"
    if version:
        url = f"{url}?v={urllib.parse.quote(version)}"
    return redirect(url, code=302)

@app.route('/favicon.ico')
@app.route('/favicon-32x32.png')
@app.route('/favicon-48x48.png')
@app.route('/apple-touch-icon.png')
@app.route('/android-chrome-192x192.png')
@app.route('/android-chrome-512x512.png')
def serve_favicons():
    image_dir = os.path.join(STATIC_DIR, 'images')
    filename = request.path[1:]
    if filename == 'favicon.ico':
        for candidate in ('favicon.ico', 'favicons.ico'):
            if os.path.exists(os.path.join(image_dir, candidate)):
                filename = candidate
                break
    local_path = os.path.join(image_dir, filename)
    if os.path.exists(local_path):
        mimetype = 'image/png' if filename.endswith('.png') else 'image/vnd.microsoft.icon'
        return send_from_directory(image_dir, filename, mimetype=mimetype)
    return serve_images(filename)

@app.route('/site.webmanifest')
def webmanifest():
    manifest_path = os.path.join(STATIC_DIR, 'site.webmanifest')
    if os.path.exists(manifest_path):
        with open(manifest_path, 'r', encoding='utf-8') as f:
            return Response(f.read(), mimetype='application/manifest+json')
    return Response('{"name":"OK Series","icons":[]}', mimetype='application/manifest+json')

@app.route('/robots.txt')
def robots_txt():
    content = (
        "User-agent: *\n"
        "Allow: /\n"
        "Disallow: /api/\n"
        f"Sitemap: {SITE_CONFIG['site_url'].rstrip('/')}/sitemap.xml\n"
    )
    return Response(content, mimetype='text/plain')


@app.route('/sitemap.xml')
def sitemap_xml():
    base = SITE_CONFIG['site_url'].rstrip('/')
    today = datetime.now().strftime('%Y-%m-%d')

    url_entries = []
    static_urls = [f"{base}/", f"{base}/guide", f"{base}/about.html", f"{base}/privacy.html"]
    for url in static_urls:
        url_entries.append({"loc": url, "alternates": {}})

    items = CACHED_DATA.get(SITE_CONFIG['data_key'], [])
    item_pairs = {}
    for item in items:
        item_id = item.get('id')
        lang = item.get('lang', 'en')
        if not item_id:
            continue
        base_id = re.sub(r'_(en|ko)$', '', item_id)
        pair = item_pairs.setdefault(base_id, {})
        pair[lang] = f"{base}/item/{item_id}"
    for pair in item_pairs.values():
        primary = pair.get('en') or pair.get('ko')
        if primary:
            url_entries.append({"loc": primary, "alternates": pair})

    guide_pairs = {}
    for lang in ('en', 'ko'):
        for guide in CACHED_GUIDES.get(lang, []):
            gid = guide.get('id')
            if not gid:
                continue
            base_id = re.sub(r'_(en|ko)$', '', gid)
            pair = guide_pairs.setdefault(base_id, {})
            pair[lang] = f"{base}/guide/{gid}"
    for pair in guide_pairs.values():
        primary = pair.get('en') or pair.get('ko')
        if primary:
            url_entries.append({"loc": primary, "alternates": pair})

    nodes = []
    for entry in url_entries:
        alternates = entry.get("alternates", {})
        hreflangs = "".join(
            [
                f'<xhtml:link rel="alternate" hreflang="{lang}" href="{href}" />'
                for lang, href in sorted(alternates.items())
            ]
        )
        nodes.append(
            f"<url><loc>{entry['loc']}</loc><lastmod>{today}</lastmod>"
            f"<changefreq>weekly</changefreq>{hreflangs}</url>"
        )

    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">'
        + ''.join(nodes) +
        '</urlset>'
    )
    return Response(xml, mimetype='application/xml')

@app.route('/about.html')
def about():
    lang  = request.args.get('lang', 'en')
    stats = _get_footer_stats(lang)
    return render_template('about.html', **stats)

@app.route('/privacy.html')
def privacy():
    return render_template('privacy.html', site=SITE_CONFIG)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
