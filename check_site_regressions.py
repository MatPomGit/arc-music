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
        const input=panel.querySelector('input');
        for(const token of ['--track','--thumb'])record('wave '+token,style(input).getPropertyValue(token).trim(),bg,3);
      }
      const plot=document.querySelector('.affect-plot');
      if(plot){
        const bg=style(plot).backgroundColor;
        const q=[...plot.querySelectorAll('rect')].map(e=>style(e).fill);
        const surfaces=[bg,...q];
        const dot=plot.querySelector('#affect-dot');
        const axis=plot.querySelector('path');
        for(const [i,b] of surfaces.entries()){
          for(const [j,t] of [...plot.querySelectorAll('text')].entries())record('plot label '+j+' / surface '+i,style(t).fill,b,4.5);
          record('plot axis / surface '+i,style(axis).stroke,b,3);
          record('plot marker / surface '+i,style(dot).fill,b,3);
        }
        for(const input of document.querySelectorAll('.sliders input')){
          const s=style(input),bg=style(input.closest('.feature')).backgroundColor;
          for(const token of ['--track','--thumb'])record(input.id+' '+token,s.getPropertyValue(token).trim(),bg,3);
        }
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
