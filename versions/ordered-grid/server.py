"""Local motion CAPTCHA research prototype. Run: python3 server.py."""
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import io, json, random, secrets, threading, time

ROOT = Path(__file__).parent / 'static'
ITEMS = ['bird', 'boat', 'fish', 'moon', 'star', 'tree', 'leaf', 'rose', 'kite']
W, H, FRAMES, FPS = 576, 108, 48, 24
TTL = 120
LOCK = threading.Lock()
CHALLENGES = {}
LAST_REQUEST = {}

def render(words):
    # Foreground and background have the same per-frame color distribution.
    # Only their movement differs; no dark text overlay is present.
    w,h=W//2,H//2
    mask=Image.new('1',(w,h));d=ImageDraw.Draw(mask)
    font=ImageFont.load_default(size=26)
    text='  '.join(words).upper()
    while d.textbbox((0,0),text,font=font)[2]>w-20:
        font=ImageFont.load_default(size=font.size-1)
    box=d.textbbox((0,0),text,font=font)
    d.text(((w-box[2])//2,(h-(box[3]-box[1]))//2-box[1]),text,font=font,fill=1,stroke_width=2,stroke_fill=1)
    mask_data=list(mask.getdata()); rng=random.Random(secrets.randbits(128))
    foreground=[rng.random()<0.35 for _ in range(w*h)]
    background=[rng.random()<0.35 for _ in range(w*h)]
    atlas=Image.new('RGB',(W*8,H*6))
    for t in range(FRAMES):
        pixels=[]
        for y in range(h):
            for x in range(w):
                if mask_data[y*w+x]:
                    dot=foreground[y*w+(x-t)%w]
                else:
                    dot=background[y*w+x]
                pixels.append((190,221,207) if dot else (15,24,27))
        frame=Image.new('RGB',(w,h));frame.putdata(pixels)
        atlas.paste(frame.resize((W,H),Image.Resampling.NEAREST),((t%8)*W,(t//8)*H))
    out=io.BytesIO();atlas.save(out,format='PNG',optimize=True)
    return out.getvalue()

def new_challenge():
    order = random.SystemRandom().sample(ITEMS,len(ITEMS))
    options = [dict(id=secrets.token_urlsafe(10),label=label) for label in order]
    targets = random.SystemRandom().sample(options,3)
    answer = [item['id'] for item in targets]
    data = render([item['label'] for item in targets])
    ident = secrets.token_urlsafe(24)
    with LOCK:
        now = time.monotonic()
        for key in list(CHALLENGES):
            if CHALLENGES[key]['expires'] <= now: del CHALLENGES[key]
        CHALLENGES[ident] = dict(answer=answer, image=data, expires=now+TTL, used=False, options=options)
    return dict(id=ident,image='/api/image/'+ident,width=W,height=H,frames=FRAMES,fps=FPS,expiresIn=TTL,options=options,selectionCount=3)

def verify(ident, answer):
    with LOCK:
        entry=CHALLENGES.get(ident)
        if not entry or entry['expires'] <= time.monotonic(): return 410,dict(error='Challenge expired. Load a new one.')
        if entry['used']: return 409,dict(error='This challenge has already been submitted. Load a new one.')
        entry['used']=True
        return 200,dict(success=entry['answer']==answer)

class Handler(BaseHTTPRequestHandler):
    def send(self,status,data,kind='application/json'):
        if isinstance(data,dict): data=json.dumps(data).encode()
        self.send_response(status)
        self.send_header('Content-Type',kind)
        self.send_header('Content-Length',str(len(data)))
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' blob:; connect-src 'self'; frame-ancestors 'none'")
        self.end_headers()
        self.wfile.write(data)
    def do_GET(self):
        if self.path.startswith('/api/image/'):
            with LOCK:
                entry=CHALLENGES.get(self.path.removeprefix('/api/image/'))
                data=entry['image'] if entry and entry['expires']>time.monotonic() else None
            return self.send(200,data,'image/png') if data else self.send(404,dict(error='Image unavailable'))
        files={'/':('index.html','text/html; charset=utf-8'),'/app.js':('app.js','text/javascript'),'/style.css':('style.css','text/css')}
        if self.path not in files: return self.send(404,dict(error='Not found'))
        filename,kind=files[self.path]
        self.send(200,(ROOT/filename).read_bytes(),kind)
    def do_POST(self):
        # Local same-origin demo. A public integration needs tenant authentication.
        if self.headers.get('Origin') and self.headers['Origin'] != 'http://'+self.headers.get('Host',''):
            return self.send(403,dict(error='Origin not allowed'))
        if self.path == '/api/challenge':
            with LOCK:
                now=time.monotonic()
                address=self.client_address[0]
                if now-LAST_REQUEST.get(address,-10)<1: return self.send(429,dict(error='Please wait a moment before refreshing.'))
                LAST_REQUEST[address]=now
            return self.send(200,new_challenge())
        if self.path != '/api/verify': return self.send(404,dict(error='Not found'))
        try:
            length=int(self.headers.get('Content-Length','0'))
            if not 0 < length <= 2048: raise ValueError()
            body=json.loads(self.rfile.read(length))
            if not isinstance(body,dict) or not isinstance(body.get('id'),str) or not isinstance(body.get('answer'),list) or len(body['answer']) != 3 or any(not isinstance(x,str) or len(x)>64 for x in body['answer']) or len(set(body['answer'])) != 3: raise ValueError()
        except (ValueError,TypeError): return self.send(400,dict(error='Invalid answer request'))
        status,result=verify(body['id'],body['answer'])
        self.send(status,result)

if __name__=='__main__':
    print('Temporal CAPTCHA → http://127.0.0.1:8080',flush=True)
    ThreadingHTTPServer(('127.0.0.1',8080),Handler).serve_forever()
