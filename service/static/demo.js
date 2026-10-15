(async()=>{
 const widget=document.getElementById('widget'),button=document.getElementById('submit'),result=document.getElementById('result');let token='',previewOnly=false;
 widget.addEventListener('captcha:verified',e=>{token=e.detail.token;button.disabled=false;result.textContent='Ready. Submit to verify this token on the customer backend.';});
 widget.addEventListener('captcha:expired',()=>{token='';button.disabled=true;result.textContent='Complete the challenge to enable submission.';});
 try{const response=await fetch('/demo/config');if(!response.ok)throw Error('Demo configuration unavailable');const config=await response.json();previewOnly=config.previewOnly;widget.dataset.sitekey=config.sitekey;const script=document.createElement('script');script.src='/widget.js';document.head.append(script);}
 catch(e){result.textContent=e.message;}
 document.getElementById('sample').onsubmit=async e=>{e.preventDefault();button.disabled=true;if(previewOnly){result.textContent='Widget completed. On your website, your backend must redeem the token through /v1/siteverify before accepting a form.';token='';return;}try{const response=await fetch('/demo/submit',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({token})});const data=await response.json();result.textContent=data.success?'Accepted: the backend verified and consumed the token.':'Rejected: '+(data.error||'invalid token');token='';}catch{result.textContent='Could not submit. Please retry with a fresh challenge.';}};
})();
