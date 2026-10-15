import base64, hashlib, re, secrets, time
from urllib.parse import urlsplit
from server import render, WORDS, W, H, FRAMES, FPS

class ServiceError(Exception):
    def __init__(self,message,status=400):self.message,self.status=message,status

def origin(value,local=False):
    if not isinstance(value,str):raise ServiceError('Invalid origin')
    u=urlsplit(value)
    if u.scheme not in ('https','http') or not u.netloc or u.username or u.password or u.path or u.query or u.fragment:
        raise ServiceError('Use an exact origin, without a path')
    if u.scheme!='https' and not(local and u.hostname in ('127.0.0.1','localhost')):raise ServiceError('HTTPS is required')
    if any(c in value for c in [' ',"'",';','\n','\r']):raise ServiceError('Invalid origin')
    return value

def digest(value):return hashlib.sha256(value.encode()).hexdigest()

class CaptchaService:
    def __init__(self,store,local=False):self.store,self.local=store,local
    def create_site(self,name,origins,limit=100):
        if not origins or not 1<=limit<=100000:raise ServiceError('Supply origins and a valid hourly quota')
        origins=[origin(o,self.local) for o in origins]
        site='site_'+secrets.token_urlsafe(18); secret='sk_'+secrets.token_urlsafe(32)
        self.store.put('site:'+site,dict(name=name,origins=origins,hourlyLimit=limit,active=True))
        self.store.put('key:'+digest(secret),dict(sitekey=site))
        return dict(sitekey=site,secret=secret,origins=origins)
    def site(self,key,parent):
        site=self.store.get('site:'+key)
        if not site or not site['active']:raise ServiceError('Unknown site key',403)
        if parent not in site['origins']:raise ServiceError('Origin is not registered',403)
        return site
    def issue(self,key,parent,action):
        site=self.site(key,parent)
        if not re.fullmatch(r'[a-zA-Z0-9_-]{1,48}',action):raise ServiceError('Invalid action')
        hour=int(time.time())//3600
        # Reservation precedes rendering so aborted work also consumes quota.
        if not self.store.count(f'usage:{key}:{hour}',site['hourlyLimit'],(hour+1)*3600+86400):raise ServiceError('Site hourly quota exceeded',429)
        answer=secrets.choice(WORDS);ident=secrets.token_urlsafe(24);image=render(answer)
        expires=int(time.time())+120
        self.store.put('challenge:'+ident,dict(answer=answer,sitekey=key,origin=parent,action=action),expires)
        self.store.put('image:'+ident,dict(data=base64.b64encode(image).decode()),expires)
        return dict(id=ident,image='/v1/images/'+ident,width=W,height=H,frames=FRAMES,fps=FPS,expiresIn=120)
    def solve(self,ident,answer):
        if not isinstance(answer,str) or not 1<=len(answer.strip())<=32:raise ServiceError('Invalid answer')
        record=self.store.take('challenge:'+ident)
        if not record:raise ServiceError('Challenge expired or already submitted',410)
        if not secrets.compare_digest(record.pop('answer').encode(),answer.strip().lower().encode()):return dict(success=False)
        token=secrets.token_urlsafe(32)
        self.store.put('token:'+digest(token),record,int(time.time())+120)
        return dict(success=True,token=token,expiresIn=120)
    def redeem(self,secret,token,action,expected_origin):
        auth=self.store.get('key:'+digest(secret))
        if not auth:raise ServiceError('Invalid secret key',401)
        key='token:'+digest(token);record=self.store.get(key)
        if not record:return dict(success=False,error='invalid-or-used-token')
        if record['sitekey']!=auth['sitekey'] or record['action']!=action or record['origin']!=expected_origin:
            return dict(success=False,error='token-binding-mismatch')
        self.site(record['sitekey'],record['origin'])
        if not self.store.take(key):return dict(success=False,error='invalid-or-used-token')
        return dict(success=True,action=record['action'],origin=record['origin'],sitekey=record['sitekey'])
