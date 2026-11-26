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
if(["team","studies","publications"].includes(type)){
const headings=Array.from(article.querySelectorAll(":scope > h2"));
if(headings.length){
const grid=document.createElement("div");grid.className=type==="publications"?"pub-list":"section-grid";headings[0].before(grid);
for(const h of headings){
const nodes=[];let next=h.nextElementSibling;while(next&&next.tagName!=="H2"&&!next.classList.contains("study-status")){nodes.push(next);next=next.nextElementSibling}
const card=document.createElement(type==="publications"?"details":"section");card.className=type==="publications"?"pub":"section-card";
if(type==="publications"){const summary=document.createElement("summary");summary.textContent=h.textContent;card.append(summary);h.remove()}else card.append(h);
for(const n of nodes)card.append(n);grid.append(card);
}
}}
const wave=document.querySelector("#wave"), intensity=document.querySelector("#wave-intensity");
if(wave&&intensity){
const paths=Array.from(wave.querySelectorAll("path")), reduced=matchMedia("(prefers-reduced-motion: reduce)");
let frame=0, start=0;
function draw(t){const a=Number(intensity.value)/100, phase=reduced.matches?0:Math.sin(t/180)*a*28;paths.forEach((p,i)=>p.setAttribute("d","M -12 "+(95+i*9)+" C 130 "+(-45-a*100+i*13+phase)+", 175 "+(330+a*160-i*8-phase)+", 285 "+(180+i*2)+" S 450 "+(80-a*50+i*5+phase)+", 575 "+(140+i*6)))}
function tick(t){if(!start)start=t;draw(t-start);if(t-start<650&&!reduced.matches)frame=requestAnimationFrame(tick);else frame=0}
intensity.addEventListener("input",()=>{cancelAnimationFrame(frame);start=0;draw(0);if(!reduced.matches)frame=requestAnimationFrame(tick)});
reduced.addEventListener("change",()=>{cancelAnimationFrame(frame);draw(0)});
}
const val=document.querySelector("#valence"), ar=document.querySelector("#arousal"), dot=document.querySelector("#affect-dot"), out=document.querySelector("#affect-output");
if(val&&ar&&dot&&out){function update(){const x=Number(val.value),y=Number(ar.value);dot.setAttribute("cx",String(170+x*1.25));dot.setAttribute("cy",String(145-y));out.textContent=(en?"Valence: ":"Walencja: ")+x+" · "+(en?"Arousal: ":"Pobudzenie: ")+y}val.addEventListener("input",update);ar.addEventListener("input",update);update()}
})();