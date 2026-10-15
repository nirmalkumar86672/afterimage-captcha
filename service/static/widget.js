(()=>{
 const serviceOrigin=new URL(document.currentScript.src).origin;
 function mount(el){
  if(el.dataset.mounted)return;el.dataset.mounted='true';
  const frame=document.createElement('iframe');
  const params=new URLSearchParams({sitekey:el.dataset.sitekey,action:el.dataset.action||'signup',parent:location.origin});
  frame.src=`${serviceOrigin}/frame?${params}`;frame.title='Afterimage CAPTCHA';frame.width='100%';frame.height='580';frame.style.cssText='border:0;max-width:460px;display:block';
  frame.setAttribute('sandbox','allow-scripts allow-same-origin');
  const field=document.createElement('input');field.type='hidden';field.name='temporal-captcha-response';
  el.append(frame,field);
  window.addEventListener('message',event=>{
   if(event.origin!==serviceOrigin||event.source!==frame.contentWindow)return;
   const data=event.data;if(!data||data.type!=='afterimage')return;
   if(data.event==='verified'&&typeof data.token==='string'){
    field.value=data.token;el.dispatchEvent(new CustomEvent('captcha:verified',{bubbles:true,detail:{token:data.token,expiresIn:data.expiresIn}}));
   }else if(data.event==='reset'||data.event==='expired'){
    field.value='';el.dispatchEvent(new CustomEvent('captcha:expired',{bubbles:true}));
   }
  });
 }
 function init(){document.querySelectorAll('.temporal-captcha').forEach(mount);}
 window.Afterimage={render:mount};
 if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init);else init();
})();
