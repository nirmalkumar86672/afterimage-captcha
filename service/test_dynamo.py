import time
import boto3
from moto import mock_aws
from service.store import DynamoStore
from service.core import CaptchaService,ServiceError
import pytest

@mock_aws
def test_dynamo_roundtrip_and_quota(monkeypatch):
    monkeypatch.setenv('AWS_REGION','ap-south-1')
    monkeypatch.setattr('service.core.render',lambda _:b'image')
    boto3.client('dynamodb',region_name='ap-south-1').create_table(TableName='captcha-test',KeySchema=[{'AttributeName':'pk','KeyType':'HASH'}],AttributeDefinitions=[{'AttributeName':'pk','AttributeType':'S'}],BillingMode='PAY_PER_REQUEST')
    store=DynamoStore('captcha-test');svc=CaptchaService(store)
    site=svc.create_site('AWS test',['https://customer.example'],1)
    challenge=svc.issue(site['sitekey'],site['origins'][0],'signup')
    answer=store.get('challenge:'+challenge['id'])['answer']
    token=svc.solve(challenge['id'],answer)['token']
    assert svc.redeem(site['secret'],token,'signup',site['origins'][0])['success']
    assert not svc.redeem(site['secret'],token,'signup',site['origins'][0])['success']
    with pytest.raises(ServiceError) as exc:svc.issue(site['sitekey'],site['origins'][0],'signup')
    assert exc.value.status==429
    store.put('old',{'hello':'world'},int(time.time())-1)
    assert store.get('old') is None
    assert store.take('old') is None
