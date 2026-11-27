"""Focused E3.1 browser regressions; called by the existing accessibility pass."""
def check_contrast(page):
    evidence = page.evaluate("""() => {
      const records=[];
      const canvas=document.createElement('canvas');canvas.width=canvas.height=1;
      const ctx=canvas.getContext('2d');
      const rgb=c=>{ctx.clearRect(0,0,1,1);ctx.fillStyle='#000';ctx.fillStyle=c;ctx.fillRect(0,0,1,1);return [...ctx.getImageData(0,0,1,1).data]};
      const lum=c=>rgb(c).slice(0,3).map(x=>x/255).map(x=>x<=.04045?x/12.92:((x+.055)/1.055)**2.4).reduce((a,x,i)=>a+x*[.2126,.7152,.0722][i],0);
      const record=(label,fg,bg,min)=>{if(rgb(fg)[3]!==255||rgb(bg)[3]!==255)throw Error('Nonopaque contrast surface: '+label);const a=lum(fg),b=lum(bg);records.push({label,fg,bg,ratio:(Math.max(a,b)+.05)/(Math.min(a,b)+.05),min})};
      const style=e=>getComputedStyle(e);
      const panel=document.querySelector('.wave-panel');
      if(panel){
        const bg=style(panel).backgroundColor;
        for(const sel of ['.wave-control','.art-note'])record(sel,style(panel.querySelector(sel)).color,bg,4.5);
        if(panel.querySelector('input'))throw Error('Wave slider must not exist');
      }
      const plot=document.querySelector('.affect-plot');
      if(plot){
        const bg=style(plot).backgroundColor;
        const q=[...plot.querySelectorAll('rect')].map(e=>style(e).fill);
        const surfaces=[bg,...q];
        const figure=plot.closest('.affect-figure');
        const labels=[...figure.querySelectorAll('.affect-label')];
        if(labels.length!==4||plot.querySelector('text'))throw Error('Missing scalable HTML axis labels');
        for(const [j,label] of labels.entries())record('plot label '+j,style(label).color,style(figure).backgroundColor,4.5);
        const readout=figure.querySelector('.affect-point-label');
        record('point coordinate readout',style(readout).color,style(readout).backgroundColor,4.5);
        const dot=plot.querySelector('#affect-dot');
        const axis=plot.querySelector('path');
        for(const [i,b] of surfaces.entries()){
          record('plot axis / surface '+i,style(axis).stroke,b,3);
          record('plot marker / surface '+i,style(dot).fill,b,3);
          for(const line of plot.querySelectorAll('.affect-projections line'))record(line.id+' / surface '+i,style(line).stroke,b,3);
          for(const point of plot.querySelectorAll('.affect-projections circle'))record(point.id+' / surface '+i,style(point).fill,b,3);
        }
        for(const input of document.querySelectorAll('.sliders input')){
          const s=style(input),bg=style(input.closest('.feature')).backgroundColor;
          for(const token of ['--track','--thumb'])record(input.id+' '+token,s.getPropertyValue(token).trim(),bg,3);
        }
      }
      for(const panel of document.querySelectorAll('.research-publications .pub')){
        const bg=style(panel).backgroundColor;
        for(const e of panel.querySelectorAll('h3,h4,p'))record(panel.id+' '+e.tagName,style(e).color,bg,4.5);
      }
      const flow=document.querySelector('.generative-flow');
      if(flow){
        const bg=style(flow).backgroundColor;
        for(const e of flow.querySelectorAll('.gen-labels span, figcaption'))record('AI flow text',style(e).color,bg,4.5);
        for(const [sel,attr] of [['.gen-input','fill'],['.gen-latent','fill'],['.gen-pulses','fill'],['.gen-wave','stroke']])record('AI flow '+sel,style(flow.querySelector(sel))[attr],bg,3);
      }
      return records;
    }""")
    assert all(r["ratio"] >= r["min"] for r in evidence), evidence
    return evidence


def check_focus(page):
    """Follow actual Tab order and reject visual reordering of the header."""
    targets = page.locator("header a, header select")
    order = targets.evaluate_all("""nodes => nodes.map(n => {
      const r=n.getBoundingClientRect();return {x:r.x,y:r.y,h:r.height};
    })""")
    for a, b in zip(order, order[1:]):
        assert b["y"] >= a["y"] - 4, ("header visual order", a, b)
        if abs(b["y"] - a["y"]) < 4:
            assert b["x"] >= a["x"] - 1, ("header horizontal order", a, b)
    page.locator(".skip").focus()
    for i in range(targets.count()):
        page.keyboard.press("Tab")
        assert targets.nth(i).evaluate("e => document.activeElement === e"), ("header tab", i)


def check_study_content(page):
    article = page.locator(".article")
    assert article.locator(":scope > .study-status").count() == 1
    assert article.locator(".section-card .study-status").count() == 0
    assert article.locator(".section-card").count() == 3
    assert article.locator(".pub").count() == 9
    assert article.locator(".pub h3").count() == 9
    assert article.locator(".pub details").count() == 0
    for i in range(1,10):
        panel = article.locator(f".pub#msc-mus-p{i:02d}")
        assert panel.count() == 1
        assert panel.locator(".pub-question").is_visible()
        assert panel.locator(".pub-body h4").count() == 2
        assert panel.locator(".pub-body p").count() == 2
        assert panel.locator(".pub-target").is_visible()
        for selector in (".pub-instruments", ".pub-sample"):
            field = panel.locator(selector)
            assert field.count() == 1 and field.is_visible()
            assert field.locator("strong").count() == 1
            assert len(field.inner_text().strip()) > 35
        assert all(len(s.strip()) >= 80 for s in panel.locator(".pub-body p").all_text_contents())
    palettes = article.locator(".pub").evaluate_all("""nodes => nodes.map(e => ({
      bg:getComputedStyle(e).backgroundColor, edge:getComputedStyle(e).borderTopColor,
      description:parseFloat(getComputedStyle(e.querySelector('.pub-body p')).fontSize),
      question:parseFloat(getComputedStyle(e.querySelector('.pub-question')).fontSize),
      root:parseFloat(getComputedStyle(document.documentElement).fontSize)
    }))""")
    assert len({p["bg"] for p in palettes}) >= 4
    assert all(a["bg"] != b["bg"] and a["edge"] != b["edge"] for a,b in zip(palettes,palettes[1:]))
    assert all(.9*p["root"] <= p["description"] < p["question"] for p in palettes)
    assert "PAQ-S" in article.locator("#msc-mus-p04").inner_text()
    assert "480" in article.locator("#msc-mus-p03").inner_text()
    for i, targets in ((1, ("N=420",)), (8, ("N=480",)), (9, ("N=440", "600"))):
        sample = article.locator(f"#msc-mus-p{i:02d} .pub-sample").inner_text()
        assert all(target in sample for target in targets), sample
    assert all(len(s.strip()) >= 180 for s in article.locator("#msc-mus-p01 .pub-body p, #msc-mus-p02 .pub-body p, #msc-mus-p03 .pub-body p, #msc-mus-p04 .pub-body p").all_text_contents())
    assert article.locator(".pub-list").evaluate("e => getComputedStyle(e).gridTemplateColumns.split(' ').length") == 1
    assert article.locator(".section-card:last-child p").count() >= 1
    # Compare the full source article to the transformed article, including status.
    raw = page.context.request.get(page.url)
    assert raw.ok
    assert page.evaluate("""source => {
      const doc=new DOMParser().parseFromString(source,'text/html');
      const norm=e=>[...e.querySelectorAll('h1,h2,p')].map(n=>n.textContent.replace(/\\s+/g,' ').trim()).join(' | ');
      return norm(doc.querySelector('.article'))===norm(document.querySelector('.article'));
    }""", raw.text()), "study text changed during card transformation"


def check_text_layout(page):
    """Check text glyph boxes against clipping containers and page bounds."""
    issues = page.evaluate("""() => {
      const bad=[];
      const walker=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT);
      while(walker.nextNode()){
        const node=walker.currentNode,e=node.parentElement;
        if(!node.textContent.trim()||!e||e.closest('script,style,svg,.visually-hidden,.skip,.language-links'))continue;
        if(!e.getClientRects().length)continue;
        const range=document.createRange();range.selectNodeContents(node);
        for(const r of range.getClientRects()){
          if(!r.width||!r.height)continue;
          if(r.left < -1 || r.right > innerWidth+1)bad.push(['viewport',node.textContent.trim().slice(0,80)]);
          for(let p=e;p&&p!==document.body;p=p.parentElement){
            const s=getComputedStyle(p),q=p.getBoundingClientRect();
            if(['hidden','clip','auto','scroll'].includes(s.overflowX)&&(r.left<q.left-1||r.right>q.right+1))bad.push(['clip-x',node.textContent.trim().slice(0,80)]);
            if(['hidden','clip','auto','scroll'].includes(s.overflowY)&&(r.top<q.top-1||r.bottom>q.bottom+1))bad.push(['clip-y',node.textContent.trim().slice(0,80)]);
          }
        }
      }
      const controls=[...document.querySelectorAll('header a,header select,main summary,main input,.cta,.footer>a')].filter(e=>e.getClientRects().length);
      for(let i=0;i<controls.length;i++)for(let j=i+1;j<controls.length;j++){
        const a=controls[i].getBoundingClientRect(),b=controls[j].getBoundingClientRect();
        if(Math.min(a.right,b.right)-Math.max(a.left,b.left)>2&&Math.min(a.bottom,b.bottom)-Math.max(a.top,b.top)>2)bad.push(['controls overlap',controls[i].outerHTML.slice(0,80),controls[j].outerHTML.slice(0,80)]);
      }
      return bad;
    }""")
    assert not issues, issues


def check_zoom_reflow(page):
    """Regression: enlarged text must not retain narrow desktop columns."""
    issues = page.evaluate("""() => {
      const bad=[], root=parseFloat(getComputedStyle(document.documentElement).fontSize);
      for(const grid of document.querySelectorAll('.section-grid,.pub-list,.steps,.hero,.affect')){
        const columns=getComputedStyle(grid).gridTemplateColumns.split(' ').map(parseFloat);
        if(columns.length>2)bad.push(['too many columns at 200%',grid.className,columns]);
        if(columns.length>1&&Math.min(...columns)<15*root)bad.push(['narrow columns',grid.className,columns,root]);
      }
      for(const label of document.querySelectorAll('.affect-label')){
        const size=parseFloat(getComputedStyle(label).fontSize);
        if(size<.875*root-.1)bad.push(['axis label does not scale',label.textContent,size,root]);
      }
      return bad;
    }""")
    assert not issues, issues
