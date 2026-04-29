/**
 * OK Series shared main engine
 * - Fetches /api/items and renders map + list
 * - Handles language switch and category filtering
 */

import { CATEGORY_MAP } from './config.js';
import { initGoogleMap, renderPhotoMarkers, filterMarkers, closeInfoWindow } from './map-core.js';

// State
let allItems    = [];
let currentLang  = 'en';
let currentTheme = 'all';

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
                <p style="font-size:1.2rem;">No results found.</p>
            </div>`;
        return;
    }

    container.innerHTML = data.map(item => `
        <div class="onsen-card">
            <a href="${item.link}">
                <img src="${item.thumbnail}" class="card-thumb" alt="${item.title}" loading="lazy">
            </a>
            <div class="card-content">
                <h3 class="card-title"><a href="${item.link}">${item.title}</a></h3>
                <p class="card-summary">${item.summary}</p>
                <div class="card-meta">
                    <span>📍 ${item.address || ''}</span>
                    <span>📅 ${item.published || item.date || ''}</span>
                </div>
            </div>
        </div>
    `).join('');
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

// Event: language toggle
document.querySelectorAll('.lang-btn').forEach(btn => {
    btn.addEventListener('click', async () => {
        document.querySelectorAll('.lang-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        currentLang = btn.dataset.lang;
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
