const $=id=>document.getElementById(id);
// These public illustrations identify choices; the required sequence stays server-side.
const art={
 bird:'<path d="M42 104Q23 83 49 67Q64 21 95 55Q109 44 118 68L137 76 117 84Q109 124 67 117L43 131 49 105" fill="#77a8bd"/><path d="M58 81Q100 66 93 100Q78 114 58 81" fill="#436b8b"/><circle cx="105" cy="66" r="4" fill="#203437"/><path d="m74 117-3 20m21-20 4 20"/>',
 boat:'<path d="M25 111h112l-20 25H47Z" fill="#bd7658"/><path d="M78 25v84H32Z" fill="#fffcdf"/><path d="M85 45v64h43Z" fill="#dba85b"/><path d="M19 145q15-11 30 0t30 0 30 0 30 0" fill="none"/>',
 fish:'<path d="m42 81-24-25v53l24-22Q83 26 132 81Q86 135 42 87" fill="#edb359"/><path d="M77 57q-10 25 0 49" fill="none"/><circle cx="111" cy="77" r="4" fill="#203437"/>',
 moon:'<path d="M103 24A57 57 0 1 0 128 113A55 55 0 0 1 103 24" fill="#f3d578"/><path d="m119 36 3 7 8 2-8 3-3 8-3-8-8-3 8-2Z" fill="#fff8dd"/>',
 star:'<path d="m80 23 17 35 39 6-28 28 7 39-35-18-35 18 7-39-28-28 39-6Z" fill="#efbb4c"/>',
 tree:'<path d="M73 93h15v48H73Z" fill="#a2734b"/><path d="M29 94 51 67H40l28-31L80 18l38 49h-11l25 27Z" fill="#5c9275"/>',
 leaf:'<path d="M39 121Q10 44 128 29Q136 128 39 121" fill="#82ab62"/><path d="m28 137 78-80M56 106l-5-31m23 12 28 2" fill="none"/>',
 rose:'<path d="M80 75v69M80 113q-30 5-36-22 31-2 36 22m1 11q31 0 34-25-31 1-34 25" fill="#6a9c70"/><path d="M80 30Q52 13 48 47Q22 61 47 80Q54 105 80 87Q111 104 116 77Q140 51 110 44Q108 13 80 30" fill="#d98388"/><path d="M62 52q31-21 39 8-2 24-26 17-20-7-6-19 15-10 20 4" fill="none"/>',
 kite:'<path d="m80 18 39 53-39 44-39-44Z" fill="#e9af65"/><path d="m80 18 0 97-39-44Z" fill="#81aebb"/><path d="M80 115q29 18 0 32" fill="none"/><path d="m80 130 12-7v14Z" fill="#cf8792"/>'};
let challenge,atlas,selected=[],frame=0,playing=false,submitted=false,busy=false,started=0,deadline=0;
const ctx=$('motion').getContext('2d'),still=$('still').getContext('2d');
function status(text,type=''){$('status').textContent=text;$('status').className=type;}
function updateSelection(){
 document.querySelectorAll('.tile').forEach(b=>{const index=selected.indexOf(b.dataset.id);b.setAttribute('aria-pressed',String(index>=0));b.querySelector('.order').textContent=index>=0?index+1:'';b.disabled=!challenge||busy||submitted||(!selected.includes(b.dataset.id)&&selected.length===3);});
 $('selection-count').textContent=`${selected.length} of 3 selected`;$('undo').disabled=!selected.length||busy||submitted;$('verify').disabled=selected.length!==3||busy||submitted||!challenge;
}
function buildTiles(){
 $('tiles').replaceChildren();challenge.options.forEach(option=>{const b=document.createElement('button');b.className='tile';b.dataset.id=option.id;b.setAttribute('aria-label',option.label);b.setAttribute('aria-pressed','false');b.innerHTML=`<svg viewBox="0 0 160 160" aria-hidden="true"><g stroke="#334e48" stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round">${art[option.label]}</g></svg><span class="tile-name">${option.label}</span><span class="order"></span>`;b.onclick=()=>{if(busy||submitted)return;const index=selected.indexOf(option.id);if(index>=0)selected.splice(index,1);else if(selected.length<3)selected.push(option.id);updateSelection();};$('tiles').append(b);});
}
function draw(){if(atlas&&challenge)ctx.drawImage(atlas,(frame%8)*challenge.width,Math.floor(frame/8)*challenge.height,challenge.width,challenge.height,0,0,576,108);}
function capture(){still.drawImage($('motion'),0,0);$('frame-label').textContent=`FRAME ${String(frame+1).padStart(2,'0')} / 48`;}
function playback(){$('toggle').textContent=playing?'Pause motion':'Play motion';$('play-state').textContent=playing?'IN MOTION':'PAUSED';}
async function post(path,body={}){const res=await fetch(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});const data=await res.json();if(!res.ok)throw Error(data.error||'Request failed');return data;}
async function load(){
 busy=true;playing=false;challenge=null;atlas=null;selected=[];submitted=false;updateSelection();$('loading').hidden=false;$('loading').textContent='Preparing your challenge…';$('refresh').disabled=true;$('capture').disabled=true;$('toggle').disabled=true;status('Generating a fresh challenge…');
 try{const data=await post('/api/challenge');const image=new Image();image.src=data.image;await image.decode();challenge=data;atlas=image;frame=0;deadline=performance.now()+data.expiresIn*1000;started=performance.now();playing=!matchMedia('(prefers-reduced-motion: reduce)').matches;draw();capture();buildTiles();playback();$('loading').hidden=true;$('capture').disabled=false;$('toggle').disabled=false;status(playing?'Select three pictures in the order shown.':'Press Play motion to read the instruction.');}
 catch(e){$('loading').textContent='Could not load challenge';status(e.message,'error');}
 finally{busy=false;$('refresh').disabled=false;updateSelection();}
}
$('undo').onclick=()=>{selected.pop();updateSelection();};
$('toggle').onclick=()=>{playing=!playing;started=performance.now()-frame/24*1000;playback();};
$('capture').onclick=capture;$('refresh').onclick=load;
$('verify').onclick=async()=>{if(selected.length!==3||!challenge||busy||submitted)return;busy=true;updateSelection();$('refresh').disabled=true;try{const result=await post('/api/verify',{id:challenge.id,answer:selected});submitted=true;status(result.success?'Verified. You selected the correct order.':'That wasn’t the order. Try a new challenge.',result.success?'success':'error');}catch(e){submitted=true;status(e.message,'error');}finally{busy=false;updateSelection();$('refresh').disabled=false;}};
function tick(now){if(challenge){if(playing){frame=Math.floor((now-started)/1000*challenge.fps)%challenge.frames;draw();}const remaining=Math.max(0,Math.ceil((deadline-now)/1000));$('time-left').textContent=`${remaining}s remaining`;if(!remaining&&!submitted){submitted=true;playing=false;playback();updateSelection();status('Challenge expired. Load a new one.','error');}}requestAnimationFrame(tick);}
requestAnimationFrame(tick);load();
