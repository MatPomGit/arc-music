"""Verify the actual browser rendering, including a deployment with no cached assets."""
import sys
from playwright.sync_api import sync_playwright

PAGES = ("", "index.html", "team.html", "studies.html", "publications.html",
         "neuropsychology.html", "en.html", "en-team.html", "en-studies.html",
         "en-publications.html", "en-neuropsychology.html")

def check_render(page):
    assert page.locator("#arc-site-style").count() == 1, "Embedded CSS missing"
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
    assert page.locator("h1").is_visible()

def run(base):
    base = base.rstrip("/") + "/"
    with sync_playwright() as p:
        for engine in (p.chromium, p.firefox):
            browser = engine.launch()
            for width in (360, 1440):
                with browser.new_context(viewport={"width": width, "height": 900}) as context:
                    page = context.new_page()
                    errors = []
                    page.on("pageerror", lambda e: errors.append(str(e)))
                    # Reproduce unavailable or stale standalone CSS/JS: the page
                    # must not depend on these resources at all.
                    context.route("**/*", lambda route: route.abort() if route.request.resource_type in ("stylesheet", "script") else route.continue_())
                    for path in PAGES:
                        response = page.goto(base + path, wait_until="load")
                        assert response and response.ok, (engine.name, path)
                        check_render(page)
                        page.locator("#theme").select_option("dark")
                        assert page.evaluate("document.documentElement.dataset.theme") == "dark"
                        page.locator("#theme").select_option("light")
                        assert page.evaluate("document.documentElement.dataset.theme") == "light"
                        if page.locator("#valence").count():
                            before = page.locator("#affect-dot").get_attribute("cx")
                            page.locator("#valence").focus()
                            page.keyboard.press("ArrowRight")
                            assert page.locator("#affect-dot").get_attribute("cx") != before
                        assert not errors, errors
                    print(f"PASS: {engine.name}, {width}px, all 11 routes", flush=True)
            browser.close()

if __name__ == "__main__":
    run(sys.argv[1])
