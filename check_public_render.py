"""Verify cold, warm and resource-blocked browser rendering."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PAGES = ("", "index.html", "team.html", "studies.html", "publications.html",
         "neuropsychology.html", "en.html", "en-team.html", "en-studies.html",
         "en-publications.html", "en-neuropsychology.html")


def identity(path):
    name = path.removesuffix(".html") or "index"
    lang = "en" if name == "en" or name.startswith("en-") else "pl"
    section = "index" if name == "en" else name.removeprefix("en-")
    return lang, section


def check_identity(page, base, path):
    lang, section = identity(path)
    assert page.url == base + path, (path, page.url)
    assert page.locator("html").get_attribute("lang") == lang, path
    assert page.locator("body").get_attribute("data-section") == section, path
    active = page.locator("nav a[aria-current=page]")
    section = "studies" if section == "publications" else section
    expected = ("en.html" if section == "index" else "en-" + section + ".html") if lang == "en" else section + ".html"
    assert active.count() == 1 and active.get_attribute("href") == expected, path


def check_assets(page, css, js):
    for selector, source in (("#arc-site-style", css), ("script:not([src])", js)):
        node = page.locator(selector)
        assert node.count() == 1 and node.text_content() == source, selector


def check_render(page):
    result = page.evaluate("""() => {
      const logo = document.querySelector('.mark svg');
      const skip = document.querySelector('.skip');
      const rect = logo.getBoundingClientRect();
      return {width: rect.width, height: rect.height,
              skip: getComputedStyle(skip).position,
              skipWidth: skip.getBoundingClientRect().width,
              nav: getComputedStyle(document.querySelector('.nav')).display,
              token: getComputedStyle(document.documentElement).getPropertyValue('--bg').trim(),
              overflow: document.documentElement.scrollWidth > innerWidth + 1};
    }""")
    assert 40 <= result["width"] <= 64 and 40 <= result["height"] <= 64, result
    assert result["skip"] == "absolute" and result["skipWidth"] <= 2, result
    assert result["nav"] == "flex" and result["token"] and not result["overflow"], result
    assert page.locator("h1").count() == 1 and page.locator("h1").is_visible()


def theme_state(page, theme):
    assert page.evaluate("document.documentElement.dataset.theme") == theme
    assert page.evaluate("getComputedStyle(document.documentElement).colorScheme") == theme
    return page.evaluate("getComputedStyle(document.body).backgroundColor")


def check_interactions(page, section):
    assert page.locator("input[type=range]").count() == 0
    if section in ("index", "neuropsychology", "studies"):
        assert page.locator("#motion-toggle").is_hidden()
        page.emulate_media(reduced_motion="no-preference")
        toggle = page.locator("#motion-toggle")
        toggle.wait_for(state="visible")
        selector, attr = ("#wave path", "d") if section == "index" else ("#affect-dot", "cx")
        if section != "studies":
            marker = page.locator(selector).first
            before = marker.get_attribute(attr)
            page.wait_for_function("(x) => document.querySelector(x[0]).getAttribute(x[1]) !== x[2]", arg=[selector, attr, before])
        if section in ("index", "studies"):
            assert page.locator(".step h3").count() == 4
            assert page.locator(".step p").count() == 4
            assert page.locator(".step-active").count() == 1
            if section == "studies":
                first = page.locator(".step-active").inner_text()
                page.wait_for_function("(x) => document.querySelector('.step-active')?.innerText !== x", arg=first, timeout=8000)
                assert page.locator(".step-active").count() == 1
        toggle.click()
        assert page.locator("html").evaluate("e => e.classList.contains('motion-paused')")
        if section != "studies":
            before = marker.get_attribute(attr)
            page.wait_for_timeout(180)
            assert marker.get_attribute(attr) == before
        page.emulate_media(reduced_motion="reduce")
        assert toggle.is_hidden()
        assert page.locator(".step-active").count() == 0
    if section == "studies":
        assert page.locator(".pub").count() == 9
        assert all(page.locator(".pub h3").nth(i).is_visible() for i in range(9))
        assert page.locator(".pub details").count() == 0
    if section == "publications":
        assert page.locator(".article a[href$='studies.html']").count() == 1
    if section == "team":
        assert page.locator(".section-card").count() == 4


def visit(page, base, path, css, js):
    response = page.goto(base + path, wait_until="load")
    assert response and response.ok, path
    check_identity(page, base, path)
    check_assets(page, css, js)
    check_render(page)


def run(base):
    from playwright.sync_api import sync_playwright
    base = base.rstrip("/") + "/"
    css = (ROOT / "pages/style.css").read_text(encoding="utf-8")
    js = (ROOT / "pages/language.js").read_text(encoding="utf-8")
    with sync_playwright() as p:
        for engine in (p.chromium, p.firefox):
            browser = engine.launch()
            try:
                for width in (360, 1440):
                    for blocked in (False, True):
                        with browser.new_context(viewport={"width": width, "height": 900}, reduced_motion="reduce") as context:
                            # Only the fault scenario intercepts traffic; normal HTTP cache remains enabled.
                            if blocked:
                                context.route("**/*", lambda route: route.abort() if route.request.resource_type in ("stylesheet", "script") else route.continue_())
                            page = context.new_page()
                            errors, external, standalone = [], [], []
                            page.on("pageerror", lambda e: errors.append(str(e)))
                            page.on("request", lambda req: external.append(req.url) if not req.url.startswith(base) else None)
                            page.on("request", lambda req: standalone.append(req.url) if req.resource_type in ("stylesheet", "script") else None)
                            for path in PAGES:
                                visit(page, base, path, css, js)
                                page.locator("#theme").select_option("dark")
                                dark = theme_state(page, "dark")
                                page.locator("#theme").select_option("light")
                                light = theme_state(page, "light")
                                assert dark != light, path
                                check_interactions(page, identity(path)[1])
                                if not blocked:
                                    visit(page, base, path, css, js)
                                    assert theme_state(page, "light") == light
                            # Explicit returning-English scenario, with same storage and no referring page.
                            visit(page, base, "en.html", css, js)
                            returning = context.new_page()
                            returning.on("pageerror", lambda e: errors.append(str(e)))
                            returning.on("request", lambda req: external.append(req.url) if not req.url.startswith(base) else None)
                            returning.on("request", lambda req: standalone.append(req.url) if req.resource_type in ("stylesheet", "script") else None)
                            returning.goto(base, wait_until="load")
                            returning.wait_for_url(base + "en.html")
                            check_identity(returning, base, "en.html")
                            check_assets(returning, css, js)
                            check_render(returning)
                            theme_state(returning, "light")
                            returning.locator("header a[hreflang=pl]").click()
                            check_identity(returning, base, "index.html")
                            assert not errors and not external and not standalone, (errors, external, standalone)
                        print(f"PASS: {engine.name}, {width}px, {'blocked' if blocked else 'normal/warm'}, all 11 routes", flush=True)
            finally:
                browser.close()


if __name__ == "__main__":
    run(sys.argv[1])
