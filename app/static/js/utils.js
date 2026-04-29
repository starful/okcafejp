import { CATEGORY_MAP, THEME_COLORS } from './config.js';

/**
 * Return theme keys from category labels
 * ex) ["Tonkotsu", "Local Gem"] → ["tonkotsu", "local"]
 */
export function getThemesFromCategories(categories = []) {
    const reverseMap = {};
    for (const [key, val] of Object.entries(CATEGORY_MAP)) {
        reverseMap[val.toLowerCase()] = key;
        reverseMap[key.toLowerCase()]  = key;
    }
    return categories.map(c => reverseMap[c.toLowerCase()] || 'default');
}

/**
 * Return one representative theme from categories
 */
export function findMainTheme(categories = []) {
    const themes = getThemesFromCategories(categories);
    return themes[0] || 'default';
}

/**
 * Return color for a theme key
 */
export function getThemeColor(theme) {
    return THEME_COLORS[theme] || THEME_COLORS['default'];
}
