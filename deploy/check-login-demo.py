"""End-to-end test of our demo using its own operator-visible challenge fixture."""
import json,urllib.request,urllib.error,http.cookiejar
from pathlib import Path
from importlib.util import spec_from_file_location,module_from_spec
spec=spec_from_file_location('p',Path(__file__).with_name('prepare-express.py'));p=module_from_spec(spec);spec.loader.exec_module(p)
c=json.loads((p.LOCAL/'customer-production.secret.json').read_text());origin=c['origins'][0]
client=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
def req(path,data=None):
    r=urllib.request.Request(origin+path,data=json.dumps(data).encode() if data is not None else None,headers={'Content-Type':'application/json','Origin':origin})
    try:
        with client.open(r,timeout=30) as response:return response.status,response.read(),response.headers
    except urllib.error.HTTPError as e:return e.code,e.read(),e.headers
assert req('/login-demo/')[0]==200
assert req('/login-demo/login',{})[0]==400
status,body,_=req('/v1/challenges',dict(sitekey=c['sitekey'],parent=origin,action='login'));assert status==200
challenge=json.loads(body)
item=p.call('dynamodb','get-item',TableName=p.state['table'],Key={'pk':{'S':'challenge:'+challenge['id']}},ConsistentRead=True)['Item']
answer=json.loads(item['payload']['S'])['answer']
status,body,_=req('/v1/solve',{'id':challenge['id'],'answer':answer});assert status==200
token=json.loads(body)['token'];data={'token':token,'email':'demo@example.com','password':'DemoPass123!'}
status,body,headers=req('/login-demo/login',data);assert status==200 and json.loads(body)['success']
assert 'Secure' in headers['Set-Cookie'] and 'HttpOnly' in headers['Set-Cookie']
for _ in range(5):assert b"You're right at home." in req('/login-demo/')[1]
assert req('/login-demo/login',data)[0]==400
assert b'Sign in to Stillroom' in req('/login-demo/logout',{})[1]
print('PASS: live login, secure session, repeated authenticated requests, replay rejection, logout.')
