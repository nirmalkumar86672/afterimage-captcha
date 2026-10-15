"""Provision private hosted-demo config and deploy an already successful build."""
import json,secrets
from pathlib import Path
from importlib.util import spec_from_file_location,module_from_spec
spec=spec_from_file_location('prepare',Path(__file__).with_name('prepare-express.py'));p=module_from_spec(spec);spec.loader.exec_module(p)
s=p.state
if __name__=='__main__':
    build=p.call('codebuild','batch-get-builds',ids=[s['buildId']])['builds'][0]
    if build['buildStatus']!='SUCCEEDED':raise SystemExit('Build is '+build['buildStatus'])
    result=p.call('ecs','describe-express-gateway-service',serviceArn=s['serviceArn'])['service']
    config=result['activeConfigurations'][0]
    origin='https://'+s['url'].removeprefix('https://')
    private=json.loads((p.LOCAL/'customer-production.secret.json').read_text())
    key={'pk':{'S':'internal:login-demo'}}
    if not p.call('dynamodb','get-item',TableName=s['table'],Key=key).get('Item'):
        record={'sitekey':private['sitekey'],'secret':private['secret'],'sessionKey':secrets.token_urlsafe(48)}
        p.call('dynamodb','put-item',TableName=s['table'],Item={**key,'payload':{'S':json.dumps(record)}},ConditionExpression='attribute_not_exists(pk)')
    image=p.call('ecr','describe-images',repositoryName=s['prefix'],imageIds=[{'imageTag':s['imageTag']}])['imageDetails'][0]
    container=config['primaryContainer']
    s['previousImage']=container['image'];p.save()
    container['image']=s['repository']+'@'+image['imageDigest']
    container['environment']=[e for e in container.get('environment',[]) if e['name']!='LOGIN_DEMO_ORIGIN']+[{'name':'LOGIN_DEMO_ORIGIN','value':origin}]
    p.call('ecs','update-express-gateway-service',serviceArn=s['serviceArn'],primaryContainer=container)
    s['imageDigest']=image['imageDigest'];s['loginDemoUrl']=origin+'/login-demo/';p.save()
    print('Deployment started:',s['loginDemoUrl'])
