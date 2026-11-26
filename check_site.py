"""Browser smoke test for the built site; run after mkdocs build."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import shutil
import threading

from playwright.sync_api import sync_playwright

PAGES = ("index", "team", "studies", "publications", "neuropsychology")
EN = ("en", "en-team", "en-studies", "en-publications", "en-neuropsychology")
ROOT = Path(__file__).resolve().parent

def main():
    assert (ROOT / "site/index.html").is_file(), "Build the website first"
    server = ThreadingHTTPServer(("127.0.0.1", 0),
        partial(SimpleHTTPRequestHandler, directory=ROOT / "site"))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_port}/"
    out = ROOT / "site-checks"
    out.mkdir(exist_ok=True)
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(executable_path=shutil.which("google-chrome") or shutil.which("chromium"), args=["--no-sandbox"])
            for width in (360, 768, 1024, 1440):
                context = browser.new_context(viewport={"width": width, "height": 900})
                page = context.new_page()
                for lang, names in (("pl", PAGES), ("en", EN)):
                    for name in names:
                        response = page.goto(base + name + ".html")
                        assert response and response.ok, name
                        page.wait_for_function("document.documentElement.lang === " + repr(lang))
                        metrics = page.evaluate("""() => ({
                            viewport: document.documentElement.clientWidth,
                            scroll: document.documentElement.scrollWidth,
                            body: parseFloat(getComputedStyle(document.querySelector('[role="main"]')).fontSize),
                            title: parseFloat(getComputedStyle(document.querySelector('[role="main"] h1')).fontSize),
                            line: parseFloat(getComputedStyle(document.querySelector('[role="main"]')).lineHeight),
                        })""")
                        assert metrics["scroll"] <= metrics["viewport"] + 1, (name, width, metrics)
                        assert 17 <= metrics["body"] <= 19, (name, width, metrics)
                        assert 30 <= metrics["title"] <= 54, (name, width, metrics)
                        assert metrics["line"] >= metrics["body"] * 1.55, (name, width, metrics)
                page.goto(base + "publications.html")
                if width < 992:
                    page.locator(".navbar-toggler").first.click()
                page.locator('#navbar-collapse a[hreflang="en"]').click()
                page.wait_for_url("**/en-publications.html")
                if width < 992:
                    page.locator(".navbar-toggler").first.click()
                page.locator("#theme-menu").click()
                page.locator('[data-bs-theme-value="dark"]').click()
                page.wait_for_function("document.documentElement.dataset.bsTheme === 'dark'")
                page.reload()
                page.wait_for_function("document.documentElement.dataset.bsTheme === 'dark'")
                page.screenshot(path=out / f"publications-dark-{width}.png", full_page=True)
                page.goto(base + "index.html")
                if width < 992:
                    page.locator(".navbar-toggler").first.click()
                page.locator("#theme-menu").click()
                page.locator('[data-bs-theme-value="light"]').click()
                page.wait_for_function("document.documentElement.dataset.bsTheme === 'light'")
                page.screenshot(path=out / f"home-light-{width}.png", full_page=True)
                print(f"PASS: 10 pages, language, theme and typography at {width}px")
                context.close()
            browser.close()
    finally:
        server.shutdown()
        server.server_close()

if __name__ == "__main__":
    main()
