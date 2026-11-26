"""Browser checks: all ten pages, two themes and five viewport widths."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import os
import json
import shutil
import threading
from playwright.sync_api import sync_playwright
from check_public_render import run as check_browser_render
from check_site_regressions import check_contrast, check_focus, check_text_layout, check_study_content, check_zoom_reflow

ROOT=Path(__file__).resolve().parent
PAGES=("index","team","studies","publications","neuropsychology","en","en-team","en-studies","en-publications","en-neuropsychology")
def accessibility(browser, base, out):
    """Additional WCAG checks, separate from the screenshot matrix."""
    axe_path = Path(os.environ["AXE_PATH"])
    assert axe_path.is_file(), "Pinned axe-core script missing"
    report = []
    failures = []
    for width in (320, 1440):
        ctx = browser.new_context(viewport={"width": width, "height": 900}, reduced_motion="reduce")
        page = ctx.new_page()
        for theme in ("light", "dark"):
            page.goto(base + "index.html")
            page.locator("#theme").select_option(theme)
            for name in PAGES:
                assert page.goto(base + name + ".html").ok
                page.wait_for_function("document.documentElement.dataset.theme === " + repr(theme))
                page.add_script_tag(path=axe_path)
                result = page.evaluate("""async () => await axe.run(document, {
                    runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21a','wcag21aa','wcag22aa']}
                })""")
                entry = {"page":name,"theme":theme,"width":width,
                    "violations":[{"id":v["id"],"impact":v["impact"],"nodes":[n["target"] for n in v["nodes"]]} for v in result["violations"]],
                    "incomplete":[{"id":v["id"],"nodes":[{"target":n["target"],"html":n["html"],"failureSummary":n.get("failureSummary"),"any":n.get("any"),"all":n.get("all"),"none":n.get("none")} for n in v["nodes"]]} for v in result["incomplete"]]}
                report.append(entry)
                entry["contrast_evidence"] = check_contrast(page)
                check_focus(page)
                if "studies" in name:
                    check_study_content(page)
                # Return to a fresh page before the existing skip-link checks.
                page.reload()
                page.wait_for_function("document.documentElement.dataset.theme === " + repr(theme))
                if entry["violations"]:
                    failures.append(entry)
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1"), (name,theme,width,"reflow")
                page.keyboard.press("Tab")
                assert page.evaluate("document.activeElement.classList.contains('skip')"), (name,theme,width,"skip link")
                page.keyboard.press("Enter")
                assert page.evaluate("document.activeElement.id === 'main'"), (name,theme,width,"skip target")
                assert page.locator("audio,video").count()==0
                assert page.locator("header a[hreflang]").count()==2
                assert page.locator("#theme").get_attribute("id")=="theme"
                assert page.evaluate("""() => Array.from(document.querySelectorAll('header a, header select, summary, main button, input[type=range]')).filter(e=>e.getClientRects().length).every(e=>{const r=e.getBoundingClientRect();return r.width>=24&&r.height>=24})"""), (name,theme,width,"target size")
                page.add_style_tag(content="*{line-height:1.5!important;letter-spacing:.12em!important;word-spacing:.16em!important}p{margin-bottom:2em!important}")
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1"), (name,theme,width,"text spacing")
                if width==1440:
                    page.add_style_tag(content="html{font-size:200%!important}")
                    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1"), (name,theme,width,"text resize")
                    page.locator("details").evaluate_all("(nodes) => nodes.forEach(n => n.open = true)")
                    check_text_layout(page)
                    check_zoom_reflow(page)
                    page.screenshot(path=out/f"{name}-{theme}-text200.png",full_page=True,animations="disabled")
        ctx.close()
    print("PASS: E3.1 focused contrast, focus, content and enlarged text checks",flush=True)
    (out/"accessibility.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    assert not failures, failures
    print("PASS: 40 axe-core page/theme/viewport checks; keyboard, reflow, spacing and resize",flush=True)

def main():
    assert (ROOT/"site/index.html").is_file()
    server=ThreadingHTTPServer(("127.0.0.1",0),partial(SimpleHTTPRequestHandler,directory=ROOT/"site"))
    threading.Thread(target=server.serve_forever,daemon=True).start()
    base=f"http://127.0.0.1:{server.server_port}/"
    out=ROOT/"site-checks";out.mkdir(exist_ok=True)
    try:
        check_browser_render(base)
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
                        assert page.locator("h1").count()==1 and page.locator("h1").is_visible()
                        assert page.evaluate("""() => {const s=getComputedStyle(document.documentElement);const l=h=>{const a=h.trim().slice(1).match(/../g).map(x=>parseInt(x,16)/255).map(x=>x<=.04045?x/12.92:((x+.055)/1.055)**2.4);return a[0]*.2126+a[1]*.7152+a[2]*.0722};const ratio=(a,b)=>{const x=l(s.getPropertyValue(a)),y=l(s.getPropertyValue(b));return (Math.max(x,y)+.05)/(Math.min(x,y)+.05)};return ["--ink","--muted","--accent"].every(a=>["--bg","--paper"].every(b=>ratio(a,b)>=4.5))}"""), (name, theme, "text token contrast")
                        assert not page.locator("header").inner_text().lower().count("arc-music")
                        assert page.locator("input[type=range]").count()==0
                        if "studies" in name:
                            assert page.locator(".pub").count()==9
                            assert all(page.locator(".pub h3").nth(i).is_visible() for i in range(9))
                        if "team" in name:
                            assert page.locator(".section-card").count()==4
                            assert page.get_by_role("heading",name="Mateusz Pomianek",exact=True).count()==1
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
            accessibility(browser,base,out)
            browser.close()
    finally:
        server.shutdown();server.server_close()
if __name__=="__main__":main()
