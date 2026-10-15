"""Local motion CAPTCHA research prototype. Run: python3 server.py."""
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import io, json, secrets, threading, time

ROOT = Path(__file__).parent / 'static'
WORDS = ['wave', 'moon', 'leaf', 'bird', 'rain', 'star', 'blue', 'tree', 'fish', 'wind', 'snow', 'gold', 'sand', 'lake', 'rose', 'fern', 'mint', 'glow', 'dawn', 'dusk', 'pine', 'boat', 'home', 'hill', 'rock', 'seed', 'path', 'pond', 'kite', 'song', 'echo', 'warm']
W, H, FRAMES, FPS = 384, 240, 48, 24
TTL = 120
LOCK = threading.Lock()
CHALLENGES = {}
LAST_REQUEST = {}

def render(answer):
    w, h = W // 3, H // 3
    mask = Image.new('1', (w, h))
    d = ImageDraw.Draw(mask)
    text = answer.upper()
    size = 40
    while True:
        font = ImageFont.load_default(size=size)
        box = d.textbbox((0,0), text, font=font, stroke_width=1)
        if box[2]-box[0] <= w-12: break
        size -= 1
    x = (w-(box[2]-box[0]))//2-box[0]
    y = (h-(box[3]-box[1]))//2-box[1]
    d.text((x,y),text,font=font,fill=1,stroke_width=1,stroke_fill=1)
    fg, bg = secrets.token_bytes(w*h), secrets.token_bytes(w*h)
    inside = list(mask.getdata())
    atlas = Image.new('RGB', (W*8,H*6))
    for t in range(FRAMES):
        pixels = bytes(1 if (fg[y*w+(x-t)%w] if inside[y*w+x] else bg[((y+t)%h)*w+x]) < 85 else 0 for y in range(h) for x in range(w))
        frame = Image.frombytes('P',(w,h),pixels)
        frame.putpalette([15,24,27,190,221,207]+[0]*762)
        atlas.paste(frame.convert('RGB').resize((W,H),Image.Resampling.NEAREST),((t%8)*W,(t//8)*H))
    out = io.BytesIO()
    atlas.save(out,format='PNG',optimize=True)
    return out.getvalue()

def new_challenge():
    answer = secrets.choice(WORDS)
    data = render(answer)
    ident = secrets.token_urlsafe(24)
    with LOCK:
        now = time.monotonic()
        for key in list(CHALLENGES):
            if CHALLENGES[key]['expires'] <= now: del CHALLENGES[key]
        CHALLENGES[ident] = dict(answer=answer, image=data, expires=now+TTL, used=False)
    return dict(id=ident,image='/api/image/'+ident,width=W,height=H,frames=FRAMES,fps=FPS,expiresIn=TTL)

def verify(ident, answer):
    with LOCK:
        entry=CHALLENGES.get(ident)
        if not entry or entry['expires'] <= time.monotonic(): return 410,dict(error='Challenge expired. Load a new one.')
        if entry['used']: return 409,dict(error='This challenge has already been submitted. Load a new one.')
        entry['used']=True
        return 200,dict(success=secrets.compare_digest(entry['answer'].encode(),answer.strip().lower().encode()))

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
            if not isinstance(body,dict) or not isinstance(body.get('id'),str) or not isinstance(body.get('answer'),str) or not 1 <= len(body['answer'].strip()) <= 32: raise ValueError()
        except (ValueError,TypeError): return self.send(400,dict(error='Invalid answer request'))
        status,result=verify(body['id'],body['answer'])
        self.send(status,result)

if __name__=='__main__':
    print('Temporal CAPTCHA → http://127.0.0.1:8080',flush=True)
    ThreadingHTTPServer(('127.0.0.1',8080),Handler).serve_forever()
