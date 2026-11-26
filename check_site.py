"""Browser checks: all ten pages, two themes and five viewport widths."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import shutil
import threading
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parent
PAGES=("index","team","studies","publications","neuropsychology","en","en-team","en-studies","en-publications","en-neuropsychology")
def main():
    assert (ROOT/"site/index.html").is_file()
    server=ThreadingHTTPServer(("127.0.0.1",0),partial(SimpleHTTPRequestHandler,directory=ROOT/"site"))
    threading.Thread(target=server.serve_forever,daemon=True).start()
    base=f"http://127.0.0.1:{server.server_port}/"
    out=ROOT/"site-checks";out.mkdir(exist_ok=True)
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch(executable_path=shutil.which("google-chrome") or shutil.which("chromium"),args=["--no-sandbox"])
            for width in (360,768,1024,1440,1920):
                context=browser.new_context(viewport={"width":width,"height":900},reduced_motion="reduce")
                page=context.new_page();errors=[];external=[]
                page.on("pageerror",lambda e:errors.append(str(e)))
                page.on("request",lambda req:external.append(req.url) if not req.url.startswith(base) else None)
                page.goto(base+"index.html")
                for theme in ("light","dark"):
                    page.locator("#theme").select_option(theme)
                    for name in PAGES:
                        assert page.goto(base+name+".html").ok
                        page.wait_for_function("document.documentElement.dataset.theme === "+repr(theme))
                        assert page.locator("html").get_attribute("lang")==("en" if name.startswith("en") else "pl")
                        assert page.locator("main").count()==1
                        assert page.locator("nav a[aria-current=page]").count()==1
                        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1"),(name,width)
                        assert page.locator("h1").first.is_visible()
                        assert not page.locator("header").inner_text().lower().count("arc-music")
                        if "publications" in name:
                            assert page.locator(".pub").count()==9
                            page.locator(".pub summary").first.focus()
                            page.keyboard.press("Enter")
                            assert page.locator(".pub").first.get_attribute("open") is not None
                        if "team" in name:
                            assert page.locator(".section-card").count()==4
                            assert page.get_by_role("heading",name="Mateusz Pomianek",exact=True).count()==1
                        if name in ("index","en"):
                            before=page.locator("#wave path").first.get_attribute("d")
                            page.locator("#wave-intensity").focus();page.keyboard.press("ArrowRight")
                            assert before!=page.locator("#wave path").first.get_attribute("d")
                        if page.locator("#valence").count():
                            before=page.locator("#affect-dot").get_attribute("cx")
                            page.locator("#valence").focus();page.keyboard.press("ArrowRight")
                            assert before!=page.locator("#affect-dot").get_attribute("cx")
                        page.screenshot(path=out/f"{name}-{theme}-{width}.png",full_page=True,animations="disabled")
                    print(f"PASS: {theme} / {width}: ten pages",flush=True)
                page.goto(base+"publications.html")
                page.locator("a[hreflang=en]").click()
                assert page.url.endswith("en-publications.html")
                page.locator("#theme").select_option("auto")
                page.emulate_media(color_scheme="dark")
                assert page.evaluate("getComputedStyle(document.documentElement).colorScheme")== "dark"
                page.emulate_media(color_scheme="light")
                assert page.evaluate("getComputedStyle(document.documentElement).colorScheme")== "light"
                assert not errors,errors
                assert not external,external
                context.close()
            browser.close()
    finally:
        server.shutdown();server.server_close()
if __name__=="__main__":main()
