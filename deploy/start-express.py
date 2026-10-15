"""Create the HTTPS service from a successfully built immutable ECR image."""
import json
from pathlib import Path
from importlib.util import spec_from_file_location,module_from_spec
spec=spec_from_file_location('prepare',Path(__file__).with_name('prepare-express.py'));p=module_from_spec(spec);spec.loader.exec_module(p)
s=p.state
if __name__=='__main__':
    build=p.call('codebuild','batch-get-builds',ids=[s['buildId']])['builds'][0]
    if build['buildStatus']!='SUCCEEDED':raise SystemExit('Build is '+build['buildStatus']+'; service creation deferred')
    image=p.call('ecr','describe-images',repositoryName=s['prefix'],imageIds=[{'imageTag':s['imageTag']}])['imageDetails'][0]
    s['imageDigest']=image['imageDigest'];p.save()
    if s.get('serviceArn'):raise SystemExit('Service already exists: '+s['serviceArn'])
    config={'executionRoleArn':s['executionRole'],'infrastructureRoleArn':s['infrastructureRole'],'taskRoleArn':s['taskRole'],'serviceName':s['prefix'],'healthCheckPath':'/healthz','primaryContainer':{'image':s['repository']+'@'+s['imageDigest'],'containerPort':8080,'awsLogsConfiguration':{'logGroup':s['apiLogs'],'logStreamPrefix':'api'},'environment':[{'name':'APP_ENV','value':'production'},{'name':'AWS_REGION','value':s['region']},{'name':'DYNAMODB_TABLE','value':s['table']},{'name':'PUBLIC_DEMO_SITEKEY','value':s['publicSitekey']}]},'cpu':'1024','memory':'2048','cpuArchitecture':'X86_64','scalingTarget':{'minTaskCount':1,'maxTaskCount':2,'autoScalingMetric':'AVERAGE_CPU','autoScalingTargetValue':60},'tags':[{'key':'Project','value':'afterimage'}]}
    result=p.call('ecs','create-express-gateway-service',**config)
    s['serviceArn']=result['service']['serviceArn'];s['cluster']=result['service']['cluster'];p.save()
    print(json.dumps(result,indent=2))
