(() => {
"use strict";
const root=document.documentElement, en=root.lang==="en";
const read=k=>{try{return localStorage.getItem(k)}catch{return null}};
const save=(k,v)=>{try{localStorage.setItem(k,v)}catch{}};
const key="arc-music-language", themeKey="arc-music-theme";
if(!en&&location.pathname.endsWith("/")&&!location.search&&!location.hash&&read(key)==="en"&&!document.referrer.startsWith(location.origin+location.pathname)){location.replace("en.html");return}
save(key,root.lang);
const theme=document.querySelector("#theme");
function apply(v){if(!["auto","light","dark"].includes(v))v="auto";if(v==="auto")delete root.dataset.theme;else root.dataset.theme=v;theme.value=v;save(themeKey,v)}
apply(read(themeKey)||"auto");theme.addEventListener("change",()=>apply(theme.value));
const article=document.querySelector(".article");
for(const p of article.querySelectorAll("p"))if(p.textContent.trim()==="PL · EN")p.classList.add("language-links");
const type=document.body.dataset.section;
if(["team","studies"].includes(type)){
const headings=Array.from(article.querySelectorAll(":scope > h2"));
if(headings.length){
const grid=document.createElement("div");grid.className="section-grid";headings[0].before(grid);
for(const h of headings){
const nodes=[];let next=h.nextElementSibling;while(next&&next.tagName!=="H2"&&!next.classList.contains("study-status")){nodes.push(next);next=next.nextElementSibling}
const card=document.createElement("section");card.className="section-card";card.append(h);
for(const n of nodes)card.append(n);grid.append(card);
}
}}
// One local animation clock; no user input is required.
const wave=document.querySelector("#wave"), dot=document.querySelector("#affect-dot");
const paths=wave?Array.from(wave.querySelectorAll("path")):[];
const steps=Array.from(document.querySelectorAll(".step"));
const toggle=document.querySelector("#motion-toggle");
if(toggle){
  const reduced=matchMedia("(prefers-reduced-motion: reduce)");
  let paused=false, frame=0, elapsed=0, last=null, lastDraw=-Infinity;
  function draw(t){
    const a=.5+.24*Math.sin(t/3400), phase=18*Math.sin(t/2600);
    paths.forEach((p,i)=>p.setAttribute("d","M -12 "+(95+i*9)+" C 130 "+(-45-a*100+i*13+phase)+", 175 "+(330+a*160-i*8-phase)+", 285 "+(180+i*2)+" S 450 "+(80-a*50+i*5+phase)+", 575 "+(140+i*6)));
    if(dot){
      dot.setAttribute("cx",(170+105*Math.sin(t/4600)).toFixed(2));
      dot.setAttribute("cy",(145-82*Math.sin(t/6200)).toFixed(2));
    }
    const active=Math.floor(t/5200)%Math.max(1,steps.length);
    steps.forEach((step,i)=>step.classList.toggle("step-active",!reduced.matches&&i===active));
  }
  function tick(now){
    if(last!==null)elapsed+=Math.min(now-last,100);
    last=now;
    if(elapsed-lastDraw>=40){draw(elapsed);lastDraw=elapsed}
    frame=requestAnimationFrame(tick);
  }
  function sync(){
    cancelAnimationFrame(frame);frame=0;last=null;
    toggle.hidden=reduced.matches;
    toggle.textContent=paused?(en?"Resume animations":"Wznów animacje"):(en?"Pause animations":"Zatrzymaj animacje");
    if(reduced.matches){draw(0);return}
    if(!paused&&!document.hidden)frame=requestAnimationFrame(tick);
  }
  toggle.addEventListener("click",()=>{paused=!paused;sync()});
  reduced.addEventListener("change",()=>{draw(reduced.matches?0:elapsed);sync()});
  document.addEventListener("visibilitychange",sync);
  draw(0);sync();
}
})();
