(() => {
  "use strict";
  const pairs = [
    ["index.html", "en.html"],
    ["team.html", "en-team.html"],
    ["studies.html", "en-studies.html"],
    ["publications.html", "en-publications.html"]
  ];
  const key = "arc-music-language";
  const base = new URL("./", window.location.href);
  const filename = (url) => url.pathname.split("/").pop() || "index.html";
  const current = filename(new URL(window.location.href));
  const pair = pairs.find((entry) => entry.includes(current));
  if (!pair) return;
  const language = pair[1] === current ? "en" : "pl";
  const read = () => {
    try { return localStorage.getItem(key); } catch (_) { return null; }
  };
  const save = (value) => {
    try { localStorage.setItem(key, value); } catch (_) { /* URL still works. */ }
  };
  const internal = (href) => {
    if (!href) return false;
    const url = new URL(href, base);
    return url.origin === base.origin && new URL("./", url).pathname === base.pathname;
  };
  // Restore a preferred language only at the bare project landing URL.
  // Explicit HTML page URLs and internal navigation always take precedence.
  if (current === "index.html" && window.location.pathname.endsWith("/") &&
      !window.location.search && !window.location.hash &&
      !internal(document.referrer) && read() === "en") {
    window.location.replace(new URL("en.html", base).href);
    return;
  }
  save(language);
  document.documentElement.lang = language;

  const navbar = document.querySelector("#navbar-collapse");
  if (!navbar) return;
  const mainNav = navbar.querySelector("ul.navbar-nav");
  if (mainNav) {
    for (const anchor of mainNav.querySelectorAll("a[href]")) {
      const url = new URL(anchor.href);
      if (!internal(url.href)) continue;
      const match = pairs.find((entry) => entry.includes(filename(url)));
      if (match) anchor.closest("li").hidden = match[language === "pl" ? 0 : 1] !== filename(url);
    }
  }
  const brand = document.querySelector(".navbar-brand");
  if (brand) brand.href = new URL(pairs[0][language === "pl" ? 0 : 1], base).href;

  // The native navigation spans both languages. Section navigation uses the
  // four links above instead of crossing the language boundary via Next.
  for (const anchor of navbar.querySelectorAll('a[rel="prev"], a[rel="next"]')) {
    const item = anchor.closest("li");
    if (item) item.hidden = true;
  }

  const themeMenu = document.querySelector("#theme-menu");
  const themeItem = themeMenu && themeMenu.closest("li");
  if (themeItem) {
    for (const [index, label] of ["PL", "EN"].entries()) {
      const item = document.createElement("li");
      item.className = "nav-item";
      const link = document.createElement("a");
      const chosen = index === 0 ? "pl" : "en";
      link.className = "nav-link";
      link.textContent = label;
      link.href = new URL(pair[index], base).href;
      link.hreflang = chosen;
      link.lang = chosen;
      link.setAttribute("aria-label", index === 0 ? "Polski" : "English");
      if (chosen === language) {
        link.classList.add("active");
        link.setAttribute("aria-current", "page");
      }
      link.addEventListener("click", () => save(chosen));
      item.append(link);
      themeItem.before(item);
    }
    // Keep ordinary Markdown language links available when JS is disabled.
    for (const paragraph of document.querySelectorAll('[role="main"] p')) {
      if (paragraph.textContent.trim() === "PL · EN") paragraph.hidden = true;
    }
    if (language === "pl") {
      themeMenu.setAttribute("aria-label", "Zmień motyw");
      const label = themeMenu.querySelector("span");
      if (label) label.textContent = "Zmień motyw";
      const labels = { light: "Jasny", dark: "Ciemny", auto: "Systemowy" };
      for (const [value, text] of Object.entries(labels)) {
        const span = navbar.querySelector('[data-bs-theme-value="' + value + '"] span');
        if (span) span.textContent = text;
      }
      const toggler = document.querySelector(".navbar-toggler");
      if (toggler) toggler.setAttribute("aria-label", "Rozwiń nawigację");
    }
  }
})();
