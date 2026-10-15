const $=id=>document.getElementById(id);
let challenge,atlas,answer,frame=0,playing=false,submitted=false,busy=false,started=0,deadline=0;
const ctx=$('motion').getContext('2d'),still=$('still').getContext('2d');
$('answer').oninput=()=>{answer=$('answer').value.trim();$('verify').disabled=!answer||busy||submitted||!challenge;};
$('answer').onkeydown=e=>{if(e.key==='Enter'&&!$('verify').disabled)$('verify').click();};
function status(text,type=''){$('status').textContent=text;$('status').className=type;}
function draw(){if(atlas&&challenge)ctx.drawImage(atlas,(frame%8)*challenge.width,Math.floor(frame/8)*challenge.height,challenge.width,challenge.height,0,0,384,240);}
function capture(){still.drawImage($('motion'),0,0);$('frame-label').textContent=`FRAME ${String(frame+1).padStart(2,'0')} / 48`;}
function playback(){$('toggle').textContent=playing?'Pause motion':'Play motion';$('play-state').textContent=playing?'IN MOTION':'PAUSED';}
async function post(path,body={}){const res=await fetch(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});const data=await res.json();if(!res.ok)throw Error(data.error||'Request failed');return data;}
async function load(){
 busy=true;playing=false;challenge=null;answer=null;submitted=false;atlas=null;
 $('loading').hidden=false;$('loading').textContent='Preparing your challenge…';$('refresh').disabled=true;$('verify').disabled=true;$('capture').disabled=true;$('toggle').disabled=true;$('answer').disabled=true;$('answer').value='';status('Generating a fresh challenge…');
 try{const data=await post('/api/challenge');const image=new Image();image.src=data.image;await image.decode();challenge=data;atlas=image;frame=0;deadline=performance.now()+data.expiresIn*1000;started=performance.now();playing=!matchMedia('(prefers-reduced-motion: reduce)').matches;draw();capture();playback();$('loading').hidden=true;$('capture').disabled=false;$('toggle').disabled=false;$('answer').disabled=false;status(playing?'Type the hidden word to continue.':'Motion is paused for your preference. Press Play motion to begin.');}
 catch(e){$('loading').textContent='Could not load challenge';status(e.message,'error');}
 finally{busy=false;$('refresh').disabled=false;}
}
$('toggle').onclick=()=>{playing=!playing;started=performance.now()-frame/24*1000;playback();};
$('capture').onclick=capture;$('refresh').onclick=load;
$('verify').onclick=async()=>{if(!answer||!challenge||busy||submitted)return;busy=true;$('verify').disabled=true;$('refresh').disabled=true;$('answer').disabled=true;try{const result=await post('/api/verify',{id:challenge.id,answer});submitted=true;status(result.success?'Verified. You found the hidden word.':'That wasn’t the word. Try a new challenge.',result.success?'success':'error');}catch(e){submitted=true;status(e.message,'error');}finally{busy=false;$('refresh').disabled=false;}};
function tick(now){if(challenge){if(playing){frame=Math.floor((now-started)/1000*challenge.fps)%challenge.frames;draw();}const remaining=Math.max(0,Math.ceil((deadline-now)/1000));$('time-left').textContent=`${remaining}s remaining`;if(!remaining&&!submitted){submitted=true;playing=false;playback();$('verify').disabled=true;$('answer').disabled=true;status('Challenge expired. Load a new one.','error');}}requestAnimationFrame(tick);}
requestAnimationFrame(tick);load();
