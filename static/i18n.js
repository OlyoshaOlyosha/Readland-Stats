// Simple i18n loader. One JSON file per language under /static/i18n/.
// Add a new language: drop `xx.json` and expose it in SUPPORTED below.
const SUPPORTED = ["en", "ru"];

const I18N = {
  current: "en",
  strings: {},

  async load(lang) {
    if (!SUPPORTED.includes(lang)) lang = "en";
    const r = await fetch(`/static/i18n/${lang}.json`);
    if (!r.ok) throw new Error(`Cannot load i18n/${lang}.json`);
    this.strings = await r.json();
    this.current = lang;
  },

  t(key) {
    return this.strings[key] ?? key;
  },

  // Fill elements that have data-i18n (textContent) or data-i18n-placeholder (input.placeholder)
  apply(root = document) {
    root.querySelectorAll("[data-i18n]").forEach((el) => {
      el.textContent = this.t(el.dataset.i18n);
    });
    root.querySelectorAll("[data-i18n-placeholder]").forEach((el) => {
      el.placeholder = this.t(el.dataset.i18nPlaceholder);
    });
  },

  supported() {
    return SUPPORTED;
  },
};