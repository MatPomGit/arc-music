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
const projection=dot?Object.fromEntries(["proj-x","proj-y","axis-x","axis-y","value-x","value-y"].map(k=>[k,document.getElementById("affect-"+k)])):null;
const coordinateFormat=new Intl.NumberFormat(en?"en":"pl",{minimumFractionDigits:2,maximumFractionDigits:2,signDisplay:"exceptZero"});
const steps=Array.from(document.querySelectorAll(".step"));
const toggle=document.querySelector("#motion-toggle");
const motion=document.querySelector("#motion-preference"), motionStatus=document.querySelector("#motion-status");
const motionKey="arc-music-neuro-motion";
if(wave||dot||steps.length){
  const reduced=matchMedia("(prefers-reduced-motion: reduce)");
  let paused=!!motion&&read(motionKey)==="off", frame=0, elapsed=0, last=null, lastDraw=-Infinity;
  if(motion)motion.value=paused?"off":"on";
  function draw(t){
    // Closed periodic trajectories: no jump at the loop boundary.
    const w=2*Math.PI*(t%4800)/4800;
    const a=.5+.24*Math.sin(w), phase=18*Math.sin(2*w+.4);
    paths.forEach((p,i)=>p.setAttribute("d","M -12 "+(95+i*9)+" C 130 "+(-45-a*100+i*13+phase)+", 175 "+(330+a*160-i*8-phase)+", 285 "+(180+i*2)+" S 450 "+(80-a*50+i*5+phase)+", 575 "+(140+i*6)));
    if(dot){
      const q=2*Math.PI*(t%6400)/6400;
      const x=(170+105*Math.sin(q)).toFixed(2), y=(145-82*Math.sin(2*q)).toFixed(2);
      dot.setAttribute("cx",x);dot.setAttribute("cy",y);
      const px=projection["proj-x"],py=projection["proj-y"];
      px.setAttribute("x1",x);px.setAttribute("y1",y);px.setAttribute("x2",x);
      py.setAttribute("x1",x);py.setAttribute("y1",y);py.setAttribute("y2",y);
      projection["axis-x"].setAttribute("cx",x);
      projection["axis-y"].setAttribute("cy",y);
      // Cartesian coordinates: SVG y increases downward; arousal increases upward.
      const values=[(Number(x)-170)/140,(145-Number(y))/115];
      ["value-x","value-y"].forEach((key,i)=>{
        const value=coordinateFormat.format(Math.round(values[i]*100)/100||0);
        if(projection[key].textContent!==value)projection[key].textContent=value;
      });
    }
    const active=Math.floor(t/3200)%Math.max(1,steps.length);
    steps.forEach((step,i)=>step.classList.toggle("step-active",!reduced.matches&&i===active));
  }
  function tick(now){
    if(reduced.matches||paused||document.hidden){frame=0;return}
    if(last!==null)elapsed+=Math.min(now-last,100);
    last=now;
    if(elapsed-lastDraw>=16){draw(elapsed);lastDraw=elapsed}
    frame=requestAnimationFrame(tick);
  }
  function sync(){
    cancelAnimationFrame(frame);frame=0;last=null;
    root.classList.toggle("motion-paused",paused||document.hidden||reduced.matches);
    if(motionStatus){
      const state=reduced.matches?"system":paused?"off":document.hidden?"hidden":"active";
      const messages=en?{system:"Paused by system preference",off:"Motion disabled",hidden:"Paused in background",active:"Motion active"}:{system:"Ruch ograniczony przez system",off:"Ruch wyłączony",hidden:"Ruch wstrzymany w tle",active:"Ruch aktywny"};
      motionStatus.dataset.state=state;
      if(motionStatus.textContent!==messages[state])motionStatus.textContent=messages[state];
    }
    if(toggle){
      toggle.hidden=reduced.matches;
      toggle.textContent=paused?(en?"Resume animations":"Wznów animacje"):(en?"Pause animations":"Zatrzymaj animacje");
    }
    if(reduced.matches){draw(0);lastDraw=-Infinity;return}
    if(!paused&&!document.hidden)frame=requestAnimationFrame(tick);
  }
  if(toggle)toggle.addEventListener("click",()=>{paused=!paused;sync()});
  if(motion)motion.addEventListener("change",()=>{paused=motion.value==="off";save(motionKey,motion.value);sync()});
  reduced.addEventListener("change",()=>{draw(reduced.matches?0:elapsed);sync()});
  document.addEventListener("visibilitychange",sync);
  draw(0);sync();
}
})();
