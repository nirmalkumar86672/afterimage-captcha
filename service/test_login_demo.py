import secrets
from service.app import create_app
from service.core import CaptchaService
from service.store import SQLiteStore

def test_hosted_login_verifies_binding_and_session(tmp_path,monkeypatch):
    origin='https://captcha.example.com'
    store=SQLiteStore(tmp_path/'demo.db');core=CaptchaService(store)
    customer=core.create_site('Hosted demo',[origin])
    store.put('internal:login-demo',{**customer,'sessionKey':secrets.token_urlsafe(32)})
    monkeypatch.setenv('LOGIN_DEMO_ORIGIN',origin)
    app=create_app(store);client=app.test_client()
    def login(token='',request_origin=origin):
        return client.post('/login-demo/login',base_url=origin,headers={'Origin':request_origin},json={'email':'demo@example.com','password':'DemoPass123!','token':token})
    assert login().status_code==400
    issued=core.issue(customer['sitekey'],origin,'login')
    answer=store.get('challenge:'+issued['id'])['answer']
    token=core.solve(issued['id'],answer)['token']
    assert login(token,'https://untrusted.example').status_code==403
    response=login(token)
    assert response.json['success']
    assert 'Secure' in response.headers['Set-Cookie'] and 'HttpOnly' in response.headers['Set-Cookie']
    assert b"You're right at home." in client.get('/login-demo/',base_url=origin).data
    assert login(token).status_code==400
    assert client.post('/login-demo/logout',base_url=origin,headers={'Origin':'null','Sec-Fetch-Site':'cross-site'}).status_code==403
    assert client.post('/login-demo/logout',base_url=origin,headers={'Origin':'null','Sec-Fetch-Site':'same-origin'}).status_code==302
    assert b'Sign in to Stillroom' in client.get('/login-demo/',base_url=origin).data
