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
const projection=dot?Object.fromEntries(["proj-x","proj-y","axis-x","axis-y","value-x","value-y","point-label","point-x","point-y"].map(k=>[k,document.getElementById("affect-"+k)])):null;
const coordinateFormat=new Intl.NumberFormat(en?"en":"pl",{minimumFractionDigits:2,maximumFractionDigits:2,signDisplay:"exceptZero"});
const steps=Array.from(document.querySelectorAll(".step"));
const genPulses=Array.from(document.querySelectorAll("[data-gen-pulse]"));
const genWave=document.querySelector("#gen-wave");
// Paths represent an illustrative flow, not a particular neural architecture.
const genRoutes=[[[66,31],[145,55],[193,34],[242,55]],
                 [[66,79],[145,92],[193,76],[242,55]],
                 [[66,55],[145,18],[193,34],[242,55]]];
const motion=document.querySelector("#motion-preference"), motionStatus=document.querySelector("#motion-status");
const motionKey="arc-music-neuro-motion";
if(wave||dot||steps.length||genWave){
  const reduced=matchMedia("(prefers-reduced-motion: reduce)");
  let paused=!!motion&&read(motionKey)==="off", frame=0, elapsed=0, last=null, lastDraw=-Infinity;
  if(motion)motion.value=paused?"off":"on";
  function draw(t){
    // Closed periodic trajectories: no jump at the loop boundary.
    const w=2*Math.PI*(t%4800)/4800;
    const a=.5+.24*Math.sin(w), phase=18*Math.sin(2*w+.4);
    paths.forEach((p,i)=>p.setAttribute("d","M -12 "+(95+i*9)+" C 130 "+(-45-a*100+i*13+phase)+", 175 "+(330+a*160-i*8-phase)+", 285 "+(180+i*2)+" S 450 "+(80-a*50+i*5+phase)+", 575 "+(140+i*6)));
    if(genWave){
      const cycle=2720;
      genPulses.forEach((p,i)=>{
        const u=((t+i*cycle/3)%cycle)/cycle;
        const segment=Math.min(2,Math.floor(u*3)), fraction=u*3-segment;
        const a=genRoutes[i][segment], b=genRoutes[i][segment+1];
        p.setAttribute("cx",(a[0]+(b[0]-a[0])*fraction).toFixed(2));
        p.setAttribute("cy",(a[1]+(b[1]-a[1])*fraction).toFixed(2));
        p.setAttribute("opacity",Math.sin(Math.PI*u).toFixed(3));
      });
      const amplitude=20+8*Math.cos(2*Math.PI*(t%cycle)/cycle);
      genWave.setAttribute("d","M242 55 Q248 "+(55-amplitude).toFixed(2)+" 255 55 T269 55 T283 55 T297 55 T311 55 T325 55");
    }
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
        const live=projection[i===0?"point-x":"point-y"];
        if(live.textContent!==value)live.textContent=value;
      });
      // The wrapper has exactly the SVG viewBox aspect ratio. Percent coordinates
      // keep the HTML label attached to the marker at every viewport and zoom.
      const label=projection["point-label"];
      label.style.setProperty("--point-x",((Number(x)-20)/300*100)+"%");
      label.style.setProperty("--point-y",((Number(y)-20)/250*100)+"%");
      label.dataset.side=Number(x)>170?"left":"right";
    }
    const active=Math.floor(t/3200)%Math.max(1,steps.length);
    steps.forEach((step,i)=>step.classList.toggle("step-active",!reduced.matches&&i===active));
  }
  function tick(now){
    // A media-query change can become visible to RAF before its change event.
    // Reconcile the entire UI instead of silently abandoning the clock.
    if(reduced.matches||paused||document.hidden){sync();return}
    if(last!==null)elapsed+=Math.min(now-last,100);
    last=now;
    if(elapsed-lastDraw>=16){draw(elapsed);lastDraw=elapsed}
    frame=requestAnimationFrame(tick);
  }
  function sync(){
    cancelAnimationFrame(frame);frame=0;last=null;
    root.classList.toggle("motion-paused",paused||document.hidden||reduced.matches);
    if(reduced.matches){draw(0);lastDraw=-Infinity;return}
    if(!paused&&!document.hidden)frame=requestAnimationFrame(tick);
  }
  if(motion)motion.addEventListener("change",()=>{paused=motion.value==="off";save(motionKey,motion.value);sync()});
  reduced.addEventListener("change",()=>{if(!reduced.matches)draw(elapsed);sync()});
  document.addEventListener("visibilitychange",sync);
  draw(0);sync();
}
})();
