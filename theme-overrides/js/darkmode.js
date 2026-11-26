/* Local theme controller for MkDocs 1.6.1; works without highlight.js. */
(() => {
  "use strict";
  const root = document.documentElement;
  const menu = document.getElementById("theme-menu");
  const toggles = document.querySelectorAll("[data-bs-theme-value]");
  const media = window.matchMedia("(prefers-color-scheme: dark)");
  const key = "mkdocs-colormode";
  const valid = (value) => ["light", "dark", "auto"].includes(value);
  let stored = null;
  try { stored = localStorage.getItem(key); } catch (_) {}
  let preference = valid(stored) ? stored : root.getAttribute("data-bs-theme");
  if (!valid(preference)) preference = "auto";
  function apply() {
    const mode = preference === "auto" ? (media.matches ? "dark" : "light") : preference;
    root.setAttribute("data-bs-theme", mode);
    for (const [id, disabled] of [["hljs-light", mode === "dark"], ["hljs-dark", mode !== "dark"]]) {
      const sheet = document.getElementById(id);
      if (sheet) sheet.disabled = disabled;
    }
    for (const toggle of toggles) {
      const active = toggle.getAttribute("data-bs-theme-value") === preference;
      toggle.setAttribute("aria-pressed", String(active));
      if (toggle.lastElementChild) toggle.lastElementChild.classList.toggle("d-none", !active);
      if (active && menu && menu.firstElementChild && toggle.firstElementChild) {
        menu.firstElementChild.className = toggle.firstElementChild.className;
      }
    }
  }
  media.addEventListener("change", () => { if (preference === "auto") apply(); });
  for (const toggle of toggles) {
    toggle.addEventListener("click", () => {
      const value = toggle.getAttribute("data-bs-theme-value");
      if (!valid(value)) return;
      preference = value;
      try { localStorage.setItem(key, preference); } catch (_) {}
      apply();
    });
  }
  apply();
})();
