import json
from pathlib import Path
from importlib.util import spec_from_file_location,module_from_spec
spec=spec_from_file_location('prepare',Path(__file__).with_name('prepare-express.py'));p=module_from_spec(spec);spec.loader.exec_module(p)
s=p.state
if 'serviceArn' in s:
    result=p.call('ecs','describe-express-gateway-service',serviceArn=s['serviceArn'])['service']
    for config in result.get('activeConfigurations',[]):
        for path in config.get('ingressPaths',[]):
            if path.get('accessType','PUBLIC')=='PUBLIC':s['url']=path['endpoint'].rstrip('/');p.save()
    print(json.dumps({'status':result.get('status'),'url':s.get('url'),'deployment':result.get('currentDeployment')},indent=2))
else:
    result=p.call('codebuild','batch-get-builds',ids=[s['buildId']])['builds'][0]
    print(json.dumps({'build':result['buildStatus'],'phase':result['currentPhase']},indent=2))
