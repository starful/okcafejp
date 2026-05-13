/**
 * OK Series shared main engine
 * - Fetches /api/items and renders map + list
 * - Handles language switch and category filtering
 */

import { CATEGORY_MAP } from './config.js';
import { initGoogleMap, renderPhotoMarkers, filterMarkers, closeInfoWindow, itemDisplayName } from './map-core.js';

// State
let allItems    = [];
let currentLang  = document.documentElement.lang === 'ko' ? 'ko' : 'en';
let currentTheme = 'all';

const FILTER_LABELS = {
    en: {
        all: 'All',
        specialty: '☕ Specialty',
        dessert: '🍰 Dessert',
        work: '💻 Work-Friendly',
        scenic: '🌿 Scenic',
    },
    ko: {
        all: '전체',
        specialty: '☕ 스페셜티',
        dessert: '🍰 디저트',
        work: '💻 작업하기 좋은',
        scenic: '🌿 경치 좋은',
    },
};

async function loadItems(lang) {
    const res = await fetch(`/api/items?lang=${encodeURIComponent(lang)}`);
    const data = await res.json();
    const key = Object.keys(data).find(k => Array.isArray(data[k]));
    allItems = data[key] || [];

    const el = document.getElementById('last-updated-date');
    if (el) el.textContent = data.last_updated || '';
}

// App bootstrap
async function initApp() {
    try {
        await loadItems(currentLang);

        // Map ID can be passed via data attribute on #map.
        const mapEl = document.getElementById('map');
        const mapId = mapEl?.dataset.mapId || '';

        await initGoogleMap(mapId);
        updateUI();
    } catch (err) {
        console.error('OKSeries: initial load failed', err);
    }
}

// UI update
async function updateUI() {
    const filtered = getFilteredData();
    renderList(filtered);
    await renderPhotoMarkers(filtered);
    updateCounts();
    updateFilterLabels();
}

// Data filtering
function getFilteredData() {
    return allItems.filter(item => {
        let themeOk  = true;
        if (currentTheme !== 'all') {
            const mapped = CATEGORY_MAP[currentTheme] || '';
            themeOk = (item.categories || []).some(c =>
                c.toLowerCase() === currentTheme || c === mapped
            );
        }
        return themeOk;
    });
}

// List rendering
function renderList(data) {
    const container = document.getElementById('item-list');
    if (!container) return;

    if (data.length === 0) {
        container.innerHTML = `
            <div style="grid-column:1/-1; text-align:center; padding:100px 0; color:#999;">
                <p style="font-size:1.2rem;">${currentLang === 'ko' ? '검색 결과가 없습니다.' : 'No results found.'}</p>
            </div>`;
        return;
    }

    container.innerHTML = data.map(item => {
        const label = itemDisplayName(item);
        return `
        <div class="onsen-card">
            <a href="${item.link}">
                <img src="${item.thumbnail}" class="card-thumb" alt="${label}" loading="lazy">
            </a>
            <div class="card-content">
                <h3 class="card-title"><a href="${item.link}">${label}</a></h3>
                <p class="card-summary">${item.summary}</p>
                <div class="card-meta">
                    <span>📍 ${item.address || ''}</span>
                    <span>📅 ${item.published || item.date || ''}</span>
                </div>
            </div>
        </div>
    `;
    }).join('');
}

function updateFilterLabels() {
    const labels = FILTER_LABELS[currentLang] || FILTER_LABELS.en;
    document.querySelectorAll('.theme-button').forEach(btn => {
        const theme = btn.dataset.theme;
        const badge = btn.querySelector('.count-badge');
        const text = labels[theme] || theme;
        btn.innerHTML = `${text}${badge ? ` ${badge.outerHTML}` : ''}`;
    });
}

// Category count badges
function updateCounts() {
    const langData = allItems;

    // all count
    const totalEl = document.getElementById('total-items');
    const allEl   = document.getElementById('count-all');
    if (totalEl) totalEl.textContent = langData.length;
    if (allEl)   allEl.textContent   = langData.length;

    // per-theme count
    for (const [key, mapped] of Object.entries(CATEGORY_MAP)) {
        const badge = document.getElementById(`count-${key}`);
        if (!badge) continue;
        const cnt = langData.filter(i =>
            (i.categories || []).some(c =>
                c.toLowerCase() === key || c === mapped
            )
        ).length;
        badge.textContent = cnt;
    }
}

// Event: language toggle (buttons only; <a href> uses full navigation for SEO)
document.querySelectorAll('.lang-btn').forEach(btn => {
    btn.addEventListener('click', async () => {
        if (btn.tagName === 'A' && btn.getAttribute('href')) {
            return;
        }
        document.querySelectorAll('.lang-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        currentLang = btn.dataset.lang;
        document.documentElement.lang = currentLang;
        await loadItems(currentLang);
        closeInfoWindow();
        updateUI();
    });
});

// Event: category filter
document.querySelectorAll('.theme-button').forEach(btn => {
    btn.addEventListener('click', () => {
        document.querySelectorAll('.theme-button').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        currentTheme = btn.dataset.theme;
        closeInfoWindow();
        updateUI();

        // mobile: scroll to list section
        if (window.innerWidth < 768) {
            document.getElementById('list-section')?.scrollIntoView({ behavior: 'smooth' });
        }
    });
});

// Start app
initApp();
