from concurrent.futures import ThreadPoolExecutor
import time
import pytest
from service.store import SQLiteStore
from service.core import CaptchaService,ServiceError
from service.app import create_app

@pytest.fixture
def setup(tmp_path,monkeypatch):
    monkeypatch.setattr('service.core.render',lambda _:b'png-test')
    store=SQLiteStore(tmp_path/'test.db');svc=CaptchaService(store,True)
    site=svc.create_site('Test',['http://localhost:8000'],10)
    return store,svc,site

def token_for(store,svc,site):
    challenge=svc.issue(site['sitekey'],site['origins'][0],'signup')
    answer=store.get('challenge:'+challenge['id'])['answer']
    return svc.solve(challenge['id'],answer)['token']

def test_binding_replay_and_concurrent_redemption(setup):
    store,svc,site=setup;token=token_for(*setup)
    other=svc.create_site('Other',site['origins'])
    assert not svc.redeem(other['secret'],token,'signup',site['origins'][0])['success']
    assert not svc.redeem(site['secret'],token,'login',site['origins'][0])['success']
    assert not svc.redeem(site['secret'],token,'signup','https://wrong.example')['success']
    with ThreadPoolExecutor(max_workers=8) as pool:
        values=list(pool.map(lambda _:svc.redeem(site['secret'],token,'signup',site['origins'][0]),range(8)))
    assert sum(x['success'] for x in values)==1

def test_wrong_answer_consumes_challenge(setup):
    store,svc,site=setup;c=svc.issue(site['sitekey'],site['origins'][0],'signup')
    assert svc.solve(c['id'],'notaword')=={'success':False}
    with pytest.raises(ServiceError):svc.solve(c['id'],'star')

def test_expiry_and_durable_storage(setup):
    store,svc,site=setup
    store.put('token:expired',{'value':1},int(time.time())-1)
    assert store.take('token:expired') is None
    assert SQLiteStore(store.path).get('site:'+site['sitekey']) is not None

def test_quota_atomic(setup):
    store,_,_=setup
    with ThreadPoolExecutor(max_workers=12) as pool:
        outcomes=list(pool.map(lambda _:store.count('quota',3,int(time.time())+120),range(12)))
    assert sum(outcomes)==3

def test_api_and_frame_csp(setup):
    store,svc,site=setup;client=create_app(store).test_client()
    response=client.get('/frame',query_string={'sitekey':site['sitekey'],'parent':site['origins'][0]})
    assert response.status_code==200
    assert 'frame-ancestors http://localhost:8000' in response.headers['Content-Security-Policy']
    assert client.get('/frame',query_string={'sitekey':site['sitekey'],'parent':'https://evil.example'}).status_code==403
    assert client.post('/v1/challenges',json={'sitekey':site['sitekey'],'parent':'https://evil.example','action':'signup'}).status_code==403
    token=token_for(*setup)
    assert client.post('/v1/siteverify',json={'token':token,'expectedAction':'signup','expectedOrigin':site['origins'][0]}).status_code==401
    result=client.post('/v1/siteverify',headers={'Authorization':'Bearer '+site['secret']},json={'token':token,'expectedAction':'signup','expectedOrigin':site['origins'][0]})
    assert result.json['success']
    assert 'secret' not in str(client.get('/frame',query_string={'sitekey':site['sitekey'],'parent':site['origins'][0]}).data)

def test_production_hides_demo(setup,monkeypatch):
    monkeypatch.setenv('APP_ENV','production');monkeypatch.setenv('ENABLE_DEMO','1')
    client=create_app(setup[0]).test_client()
    assert client.get('/demo/config').status_code==404
    assert client.get('/').status_code==404

def test_malformed_inputs(setup):
    client=create_app(setup[0]).test_client()
    assert client.post('/v1/solve',json=[]).status_code==400
    assert client.post('/v1/solve',json={'id':'a','answer':['x']}).status_code==400
    assert client.post('/v1/solve',data='x'*5000,content_type='application/json').status_code==413


def test_public_preview_never_exposes_demo_secret(setup,monkeypatch):
    monkeypatch.setenv('APP_ENV','production')
    monkeypatch.setenv('PUBLIC_DEMO_SITEKEY',setup[2]['sitekey'])
    client=create_app(setup[0]).test_client()
    assert client.get('/').status_code==200
    assert client.get('/demo/config').json=={'sitekey':setup[2]['sitekey'],'previewOnly':True}
    assert client.post('/demo/submit',json={'token':'test'}).status_code==404
