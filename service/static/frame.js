const $=id=>document.getElementById(id),params=new URLSearchParams(location.search);
const parentOrigin=params.get('parent'),sitekey=params.get('sitekey'),action=params.get('action')||'signup';
let challenge,image,playing=false,frame=0,start=0,deadline=0,used=false,busy=false,tokenTimer;
const ctx=$('motion').getContext('2d');
function notify(event,extra={}){window.parent.postMessage({type:'afterimage',event,...extra},parentOrigin);}
function status(message){$('status').textContent=message;}
async function post(path,body){const res=await fetch(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});const value=await res.json();if(!res.ok)throw Error(value.error||'Request failed');return value;}
function controls(){ $('verify').disabled=busy||used||!challenge||!$('answer').value.trim();$('answer').disabled=busy||used||!challenge; $('refresh').disabled=busy;}
function paint(){ctx.drawImage(image,(frame%8)*384,Math.floor(frame/8)*240,384,240,0,0,384,240);}
function playback(){$('toggle').textContent=playing?'Pause motion':'Play motion';$('play-state').textContent=playing?'IN MOTION':'PAUSED';}
async function load(){
 clearTimeout(tokenTimer);notify('reset');busy=true;used=false;playing=false;challenge=null;image=null;controls();$('toggle').disabled=true;$('answer').value='';$('loading').hidden=false;$('loading').textContent='Preparing challenge…';status('');
 try{const data=await post('/v1/challenges',{sitekey,parent:parentOrigin,action});const next=new Image();next.src=data.image;await next.decode();challenge=data;image=next;frame=0;start=performance.now();deadline=start+data.expiresIn*1000;playing=!matchMedia('(prefers-reduced-motion: reduce)').matches;paint();playback();$('toggle').disabled=false;$('loading').hidden=true;status(playing?'Read the word in motion.':'Press Play motion when ready.');}
 catch(e){status(e.message);$('loading').textContent='Could not load challenge';}
 finally{busy=false;controls();}
}
$('answer').oninput=controls;$('answer').onkeydown=e=>{if(e.key==='Enter'&&!$('verify').disabled)$('verify').click();};$('refresh').onclick=load;
$('toggle').onclick=()=>{playing=!playing;start=performance.now()-frame/24*1000;playback();};
$('verify').onclick=async()=>{
 if($('verify').disabled)return;busy=true;controls();
 try{const result=await post('/v1/solve',{id:challenge.id,answer:$('answer').value});used=true;playing=false;playback();
 if(result.success){status('Verified. You can continue.');notify('verified',{token:result.token,expiresIn:result.expiresIn});tokenTimer=setTimeout(()=>{notify('expired');status('Verification expired. Load a new challenge.');},result.expiresIn*1000);}
 else status('Incorrect word. Load a new challenge.');
 }catch(e){used=true;status(e.message);}finally{busy=false;controls();}
};
function tick(now){if(challenge){if(playing){frame=Math.floor((now-start)/1000*24)%48;paint();}const seconds=Math.max(0,Math.ceil((deadline-now)/1000));$('time-left').textContent=used?'':`${seconds}s remaining`;if(!seconds&&!used){used=true;playing=false;playback();controls();status('Challenge expired. Load a new one.');notify('expired');}}requestAnimationFrame(tick);}
requestAnimationFrame(tick);load();
