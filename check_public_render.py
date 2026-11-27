"""Verify cold, warm and resource-blocked browser rendering."""
import sys
import re
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
    check_home_layout(page, page.locator("body").get_attribute("data-section"))


def check_home_layout(page, section):
    """Keep requested content removal and responsive illustration order."""
    if section == "index":
        assert page.locator(".about-layout").count() == 1
        assert page.locator(".about-layout > .generative-flow + .article").count() == 1
        assert page.locator(".about-layout > .article h2").is_visible()
        geometry = page.evaluate("""() => {
          const layout=document.querySelector('.about-layout');
          const figure=layout.querySelector('.generative-flow').getBoundingClientRect();
          const article=layout.querySelector('.article').getBoundingClientRect();
          const style=getComputedStyle(layout);
          const tracks=style.gridTemplateColumns.trim().split(/\\s+/).map(parseFloat);
          const root=parseFloat(getComputedStyle(document.documentElement).fontSize);
          const gap=parseFloat(style.columnGap);
          const width=layout.getBoundingClientRect().width;
          const threshold=48*root+gap;
          const sideBySide=tracks.length===2 && tracks.every(t=>t>=24*root-1) &&
            figure.right<=article.left+1 &&
            Math.min(figure.bottom,article.bottom)>Math.max(figure.top,article.top);
          const stacked=tracks.length===1 && figure.bottom<=article.top+1;
          const ok=width>threshold+1 ? sideBySide :
            width<threshold-1 ? stacked : (sideBySide || stacked);
          return {ok,width,threshold,tracks,root,gap,figure:figure.toJSON(),
                  article:article.toJSON(),viewport:innerWidth};
        }""")
        assert geometry["ok"], ("About illustration/text layout", geometry)
    if section in ("index","neuropsychology"):
        assert page.locator("#affect-title").count() == 0
        assert page.locator(".affect-compact > .affect-figure:only-child").count() == 1
        assert page.locator(".affect-compact").get_attribute("aria-label")
        assert page.evaluate("""() => {
          const card=document.querySelector('.affect-compact');
          const shell=card.closest('main');
          const a=card.getBoundingClientRect(), b=shell.getBoundingClientRect();
          return getComputedStyle(card).gridTemplateColumns.split(' ').length===1 &&
            Math.abs((a.left+a.right-b.left-b.right)/2)<2 &&
            a.width<=36*parseFloat(getComputedStyle(document.documentElement).fontSize)+1;
        }"""), "Affect card must be compact and centered"


def theme_state(page, theme):
    assert page.evaluate("document.documentElement.dataset.theme") == theme
    assert page.evaluate("getComputedStyle(document.documentElement).colorScheme") == theme
    return page.evaluate("getComputedStyle(document.body).backgroundColor")


def check_projections(page):
    # Read a complete frame atomically so concurrent animation cannot mix coordinates.
    assert page.evaluate("""() => {
      const n=(id,a)=>+document.getElementById('affect-'+id).getAttribute(a);
      const x=n('dot','cx'), y=n('dot','cy');
      const value=id=>Number(document.getElementById('affect-value-'+id).textContent.replace(',', '.'));
      const label=document.getElementById('affect-point-label'), wrap=label.parentElement;
      const r=label.getBoundingClientRect(), w=wrap.getBoundingClientRect(), dot=document.getElementById('affect-dot').getBoundingClientRect();
      const nearX=label.dataset.side==='left'?Math.abs(r.right-dot.right+dot.width/2):Math.abs(r.left-dot.left-dot.width/2);
      const nearY=Math.abs((r.top+r.bottom)/2-(dot.top+dot.bottom)/2);
      const localized=id=>document.getElementById('affect-point-'+id).textContent===document.getElementById('affect-value-'+id).textContent;
      return localized('x') && localized('y') && nearX<=17 && nearY<=1
        && r.left>=w.left-1 && r.right<=w.right+1 && r.top>=w.top-1 && r.bottom<=w.bottom+1
        && label.getAttribute('aria-hidden')==='true'
        && n('proj-x','x1')===x && n('proj-x','y1')===y && n('proj-x','x2')===x && n('proj-x','y2')===145
        && n('proj-y','x1')===x && n('proj-y','y1')===y && n('proj-y','x2')===170 && n('proj-y','y2')===y
        && n('axis-x','cx')===x && n('axis-x','cy')===145 && n('axis-y','cx')===170 && n('axis-y','cy')===y
        && Math.abs(value('x')-(x-170)/140)<=.0051 && Math.abs(value('y')-(145-y)/115)<=.0051;
    }"""), "Projection geometry or coordinate values are inconsistent"


def check_interactions(page, section):
    assert page.locator("input[type=range]").count() == 0
    assert page.locator("#motion-toggle, .motion-controls, #motion-preference, #motion-status").count() == 0
    assert page.locator(".generative-flow").count() == (1 if section == "index" else 0)
    if section == "index":
        lang = page.locator("html").get_attribute("lang")
        assert page.locator(".generative-flow figcaption").inner_text() == (
            "from intention to music" if lang == "en" else "od intencji do muzyki")
        assert page.locator(".generative-flow input, .generative-flow button").count() == 0
        assert page.locator("[data-gen-pulse]").count() == 3
    if section in ("index", "neuropsychology"):
        check_projections(page)
    if section == "neuropsychology":
        assert page.locator("#motion-toggle").count() == 0
        assert page.locator(".article > h2").count() >= 7
        assert page.locator(".article a[href^='https://doi.org/']").count() >= 9
        if page.viewport_size["width"] >= 1200:
            assert page.locator(".article").bounding_box()["width"] >= 850
        marker = page.locator("#affect-dot")
        before = marker.get_attribute("cx")
        page.wait_for_timeout(180)
        assert marker.get_attribute("cx") == before
        page.emulate_media(reduced_motion="no-preference")
        motion_state(page, "active")
        page.wait_for_function("(x) => document.querySelector('#affect-dot').getAttribute('cx') !== x", arg=before)
        # A substantial displacement within one second verifies the faster motion.
        page.wait_for_function("() => Math.abs(+document.querySelector('#affect-dot').getAttribute('cx')-170)>40", timeout=1500)
        check_projections(page)
        # Observe beyond the former 4.4-second stop and the 6.4-second loop boundary.
        page.wait_for_timeout(6600)
        before = marker.get_attribute("cx")
        page.wait_for_function("(x) => document.querySelector('#affect-dot').getAttribute('cx') !== x", arg=before, timeout=1000)
        check_projections(page)
        assert not page.locator("html").evaluate("e => e.classList.contains('motion-paused')")
        page.emulate_media(reduced_motion="reduce")
        motion_state(page, "system")
        page.wait_for_function("() => document.querySelector('#affect-dot').getAttribute('cx') === '170.00'", polling=50)
        page.wait_for_timeout(180)
        assert marker.get_attribute("cx") == "170.00"
        check_projections(page)
    if section in ("index", "studies"):
        page.emulate_media(reduced_motion="no-preference")
        page.wait_for_function("() => !matchMedia('(prefers-reduced-motion: reduce)').matches", polling=50)
        motion_state(page, "active")
        if section == "index":
            marker = page.locator("#wave path").first
            before = marker.get_attribute("d")
            page.wait_for_function("(x) => document.querySelector('#wave path').getAttribute('d') !== x", arg=before)
            check_projections(page)
        assert page.locator(".step h3").count() == 4
        assert page.locator(".step p").count() == 4
        page.locator(".step-active").wait_for(state="visible")
        assert page.locator(".step-active").count() == 1
        if section == "studies":
            first = page.locator(".step-active").inner_text()
            page.wait_for_function("(x) => document.querySelector('.step-active')?.innerText !== x", arg=first, timeout=8000)
            assert page.locator(".step-active").count() == 1
        page.emulate_media(reduced_motion="reduce")
        motion_state(page, "system")
        page.wait_for_function("() => !document.querySelector('.step-active')", polling=50)
        assert page.locator("html").evaluate("e => e.classList.contains('motion-paused')")
        if section == "index":
            stationary = marker.get_attribute("d")
            page.wait_for_timeout(180)
            assert marker.get_attribute("d") == stationary
            check_projections(page)
    if section == "studies":
        assert page.locator(".pub").count() == 9
        assert all(page.locator(".pub h3").nth(i).is_visible() for i in range(9))
        assert page.locator(".pub details").count() == 0
        for i in range(1,10):
            panel = page.locator(f".pub#msc-mus-p{i:02d}")
            assert panel.count() == 1
            assert panel.locator(".pub-question").is_visible()
            assert panel.locator(".pub-body h4").count() == 2
            assert panel.locator(".pub-body p").count() == 2
            assert panel.locator(".pub-target").is_visible()
            assert all(len(s.strip()) >= 80 for s in panel.locator(".pub-body p").all_text_contents())
        assert page.locator(".pub-list").evaluate("e => getComputedStyle(e).gridTemplateColumns.split(' ').length") == 1
    if section == "publications":
        assert page.locator(".article a[href$='studies.html']").count() == 1
    if section == "team":
        assert page.locator(".section-card").count() == 4



# Test-only virtual RAF queue. The production animation clock is unmodified.
# Visibility events are simulated explicitly because headless tab activation
# does not reliably change document.hidden across browser engines.
MOTION_CLOCK = """(() => {
  let now=0, next=0, hidden=false;
  const queue=new Map();
  window.requestAnimationFrame=cb=>{queue.set(++next,cb);return next};
  window.cancelAnimationFrame=id=>queue.delete(id);
  Object.defineProperty(document,'hidden',{configurable:true,get:()=>hidden});
  window.__motionTest={
    advance(target){
      if(target<now)throw Error('clock cannot run backwards');
      function frame(){const batch=[...queue];queue.clear();for(const [,cb] of batch)cb(now)}
      frame();
      while(now<target){now=Math.min(target,now+16);frame()}
    },
    visibility(value){hidden=value;document.dispatchEvent(new Event('visibilitychange'))},
    pending(){return queue.size}
  };
})()"""


def advance(page, time):
    page.evaluate("(t) => window.__motionTest.advance(t)", time)


def motion_state(page, expected):
    # The virtual RAF clock does not advance while waiting for a media-query event.
    # Playwright's default RAF polling would deadlock; use independent timer polling.
    page.wait_for_function(
        "(paused) => document.documentElement.classList.contains('motion-paused') === paused",
        arg=expected != "active", polling=50)
    assert page.evaluate("matchMedia('(prefers-reduced-motion: reduce)').matches") == (expected == "system")
    assert page.locator("#motion-preference, #motion-status").count() == 0


def point(page):
    return page.locator("#affect-dot").evaluate("e => [+e.getAttribute('cx'), +e.getAttribute('cy')]")


def wave_geometry(page):
    return [float(v) for v in re.findall(r"-?\d+(?:\.\d+)?(?:e[+-]?\d+)?",
                                        page.locator("#wave path").first.get_attribute("d"))]


def check_motion_regressions(browser, base, out=None):
    with browser.new_context(viewport={"width": 1440, "height": 900}, reduced_motion="no-preference") as ctx:
        ctx.add_init_script(MOTION_CLOCK)
        page = ctx.new_page()
        # Real animation callbacks, driven at deterministic elapsed times.
        page.goto(base + "index.html")
        advance(page, 0)
        wave0 = wave_geometry(page)
        initial = point(page)
        assert initial == [170,145], ("affect origin", initial)
        stage0 = page.locator(".step-active").inner_text()
        gen_frame = lambda: page.locator("[data-gen-pulse]").evaluate_all(
            "nodes => nodes.map(e => ['cx','cy','opacity'].map(a => e.getAttribute(a)))")
        gen0 = gen_frame()
        gen_wave0 = page.locator("#gen-wave").get_attribute("d")
        advance(page, 800)
        assert gen_frame() != gen0
        assert page.locator("#gen-wave").get_attribute("d") != gen_wave0
        advance(page, 2720)
        assert gen_frame() == gen0, "Generative animation does not close its cycle"
        assert page.locator("#gen-wave").get_attribute("d") == gen_wave0
        assert point(page) != initial, "Affect must move independently of the generative cycle"
        advance(page, 3184)
        assert page.locator(".step-active").inner_text() == stage0
        advance(page, 3200)
        assert page.locator(".step-active").inner_text() != stage0
        assert page.locator(".step-active").count() == 1
        advance(page, 4784)
        w_before = wave_geometry(page)
        advance(page, 4800)
        w_boundary = wave_geometry(page)
        advance(page, 4816)
        w_after = wave_geometry(page)
        assert w_boundary == wave0, "Wave does not close at its period"
        assert max(abs(a-b) for a,b in zip(w_before,w_after)) < 10, "Wave jumps across period"
        advance(page, 6384)
        p_before = point(page)
        check_projections(page)
        advance(page, 6400)
        assert point(page) == initial == [170,145], ("affect cycle boundary", point(page), initial)
        check_projections(page)
        advance(page, 6416)
        p_after = point(page)
        check_projections(page)
        assert max(abs(a-b) for a,b in zip(p_before,p_after)) < 6, "Affect point jumps across period"
        advance(page, 12800)
        assert page.locator(".step-active").inner_text() == stage0
        assert page.locator(".step-active").count() == 1

        # The remaining animation follows system reduced motion, without a manual control.
        page.emulate_media(reduced_motion="reduce")
        motion_state(page, "system")
        assert gen_frame() == gen0
        advance(page, 16000)
        assert gen_frame() == gen0
        page.emulate_media(reduced_motion="no-preference")
        motion_state(page, "active")

        # Check attachment and bounds over the complete orbit on a narrow phone.
        page.set_viewport_size({"width":320,"height":900})
        page.goto(base + "index.html")
        for t in range(0,6401,160):
            advance(page,t)
            check_projections(page)
        page.set_viewport_size({"width":1440,"height":900})

        # System preference remains effective across reloads and language routes.
        page.goto(base + "neuropsychology.html")
        motion_state(page, "active")
        advance(page, 800)
        assert point(page) != [170,145]
        page.emulate_media(reduced_motion="reduce")
        motion_state(page, "system")
        assert point(page) == [170,145]
        page.reload()
        motion_state(page, "system")
        advance(page, 800)
        assert point(page) == [170,145]
        page.locator("header a[hreflang=en]").click()
        motion_state(page, "system")
        advance(page, 800)
        assert point(page) == [170,145]
        page.emulate_media(reduced_motion="no-preference")
        motion_state(page, "active")
        advance(page, 4000)
        stationary = point(page)
        page.evaluate("window.__motionTest.visibility(true)")
        motion_state(page, "hidden")
        advance(page, 8000)
        assert point(page) == stationary
        assert page.evaluate("window.__motionTest.pending()") == 0
        page.evaluate("window.__motionTest.visibility(false)")
        motion_state(page, "active")
        advance(page, 8000)
        assert point(page) == stationary, "Resume must not jump"
        advance(page, 8320)
        assert point(page) != stationary
        check_projections(page)

        # Evidence from nonzero frames, in both languages and both themes.
        for path, lang in (("neuropsychology.html","pl"),("en-neuropsychology.html","en")):
            page.goto(base + path)
            motion_state(page, "active")
            advance(page, 800)
            x,y = point(page)
            assert abs(x-170)>30 and abs(y-145)>30
            check_projections(page)
            for theme in ("light","dark"):
                page.locator("#theme").select_option(theme)
                if out is not None:
                    page.locator(".affect").screenshot(path=out / f"active-affect-{lang}-{theme}.png", animations="allow")
                    page.locator(".controls").screenshot(path=out / f"active-controls-{lang}-{theme}.png", animations="allow")
        print("PASS: E3.1 deterministic cycle, persisted preference, system and visibility regressions", flush=True)


def check_motion_event_race(browser, base):
    """A frame observing reduced motion must reconcile even before its event."""
    with browser.new_context(reduced_motion="no-preference") as ctx:
        ctx.add_init_script(MOTION_CLOCK + """
;(() => {
    const nativeMatchMedia=window.matchMedia.bind(window);
    const query=nativeMatchMedia('(prefers-reduced-motion: reduce)');
    query.addEventListener('change', event => {
        if(window.__holdMotionChange)event.stopImmediatePropagation();
    });
    window.matchMedia=value=>value==='(prefers-reduced-motion: reduce)'?query:nativeMatchMedia(value);
    window.__holdMotionChange=true;
})();""")
        page=ctx.new_page()
        page.goto(base+"index.html")
        advance(page, 800)
        motion_state(page, "active")
        assert point(page) != [170,145]
        assert page.locator(".step-active").count() == 1
        page.emulate_media(reduced_motion="reduce")
        page.wait_for_function(
            "() => matchMedia('(prefers-reduced-motion: reduce)').matches",
            polling=50)
        # Deliver the outstanding frame while the media event is withheld.
        advance(page, 816)
        motion_state(page, "system")
        assert point(page) == [170,145]
        assert page.locator(".step-active").count() == 0
        assert page.evaluate("window.__motionTest.pending()") == 0
        check_projections(page)
        page.evaluate("window.__holdMotionChange=false")
        page.emulate_media(reduced_motion="no-preference")
        motion_state(page, "active")
        advance(page, 1616)
        assert point(page) != [170,145]
        assert page.locator(".step-active").count() == 1
        check_projections(page)


def navigate(page, base, path):
    response = page.goto(base + path, wait_until="load")
    # Firefox can expose HTTP 304 for a revalidated top-level document.
    # The browser must still render the cached representation of the exact route.
    assert response is not None and (response.ok or response.status == 304), (
        path, response.status if response is not None else "no response")
    check_identity(page, base, path)


def visit(page, base, path, css, js):
    navigate(page, base, path)
    check_assets(page, css, js)
    check_render(page)


def run(base, out=None):
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
                check_motion_regressions(browser, base, out if engine.name == "chromium" else None)
                check_motion_event_race(browser, base)
            finally:
                browser.close()


if __name__ == "__main__":
    run(sys.argv[1])
