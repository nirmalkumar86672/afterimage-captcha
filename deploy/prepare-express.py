"""Provision dedicated beta build/state resources through AWS CLI; resumable locally."""
import json,secrets,subprocess,zipfile,os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
LOCAL=ROOT/'.local';LOCAL.mkdir(exist_ok=True)
STATE=LOCAL/'aws-deployment.json'
AWS=str(Path.home()/'.local/bin/aws')
state=json.loads(STATE.read_text()) if STATE.exists() else {'region':'ap-south-1','profile':'afterimage','prefix':'afterimage-beta-'+secrets.token_hex(3),'publicSitekey':'site_'+secrets.token_urlsafe(18)}
def save():STATE.write_text(json.dumps(state,indent=2)+'\n')
def call(service,op,**kwargs):
    args=[AWS,service,op,'--profile',state['profile'],'--region',state['region'],'--no-cli-pager','--output','json']
    if kwargs:args+=['--cli-input-json',json.dumps(kwargs)]
    p=subprocess.run(args,capture_output=True,text=True)
    if p.returncode:raise RuntimeError(f'{service} {op}: '+p.stderr)
    return json.loads(p.stdout) if p.stdout.strip() else {}
def once(key,service,op,extract=lambda x:x,**kwargs):
    if key not in state:
        state[key]=extract(call(service,op,**kwargs));save();print('Created',key,flush=True)
    return state[key]
def policy(statements):return {'Version':'2012-10-17','Statement':statements}
def allow(actions,resources):return {'Effect':'Allow','Action':actions,'Resource':resources}
def role(label,principal,source=None):
    stmt={'Effect':'Allow','Principal':{'Service':principal},'Action':'sts:AssumeRole'}
    if source:stmt['Condition']={'StringEquals':{'aws:SourceAccount':account},'ArnLike':{'aws:SourceArn':source}}
    return once(label,'iam','create-role',lambda x:x['Role']['Arn'],RoleName=prefix+'-'+label,AssumeRolePolicyDocument=json.dumps(policy([stmt])),Tags=[{'Key':'Project','Value':'afterimage'}])
if __name__=='__main__':
    account=call('sts','get-caller-identity')['Account'];state['account']=account;save()
    prefix=state['prefix'];region=state['region'];base=f'arn:aws';repoarn=f'{base}:ecr:{region}:{account}:repository/{prefix}'
    once('repository','ecr','create-repository',lambda x:x['repository']['repositoryUri'],repositoryName=prefix,imageTagMutability='IMMUTABLE',imageScanningConfiguration={'scanOnPush':True},encryptionConfiguration={'encryptionType':'AES256'},tags=[{'Key':'Project','Value':'afterimage'}])
    once('table','dynamodb','create-table',lambda x:x['TableDescription']['TableName'],TableName=prefix,BillingMode='PAY_PER_REQUEST',AttributeDefinitions=[{'AttributeName':'pk','AttributeType':'S'}],KeySchema=[{'AttributeName':'pk','KeyType':'HASH'}],SSESpecification={'Enabled':True},Tags=[{'Key':'Project','Value':'afterimage'}])
    bucket=prefix+'-'+account
    once('bucket','s3api','create-bucket',lambda _:bucket,Bucket=bucket,CreateBucketConfiguration={'LocationConstraint':region})
    call('s3api','put-public-access-block',Bucket=bucket,PublicAccessBlockConfiguration=dict(BlockPublicAcls=True,IgnorePublicAcls=True,BlockPublicPolicy=True,RestrictPublicBuckets=True))
    call('s3api','put-bucket-encryption',Bucket=bucket,ServerSideEncryptionConfiguration={'Rules':[{'ApplyServerSideEncryptionByDefault':{'SSEAlgorithm':'AES256'}}]})
    call('s3api','put-bucket-versioning',Bucket=bucket,VersioningConfiguration={'Status':'Enabled'})
    call('s3api','put-bucket-policy',Bucket=bucket,Policy=json.dumps(policy([{'Effect':'Deny','Principal':'*','Action':'s3:*','Resource':[f'arn:aws:s3:::{bucket}',f'arn:aws:s3:::{bucket}/*'],'Condition':{'Bool':{'aws:SecureTransport':'false'}}}])))
    call('s3api','put-bucket-lifecycle-configuration',Bucket=bucket,LifecycleConfiguration={'Rules':[{'ID':'BuildSourceRetention','Status':'Enabled','Filter':{'Prefix':'source/'},'Expiration':{'Days':7},'NoncurrentVersionExpiration':{'NoncurrentDays':7}}]})
    for label in ['apiLogs','buildLogs']:
        name='/afterimage/'+prefix+'/'+label
        once(label,'logs','create-log-group',lambda _:name,logGroupName=name)
        call('logs','put-retention-policy',logGroupName=name,retentionInDays=14)
    logarn=f'arn:aws:logs:{region}:{account}:log-group:{state["buildLogs"]}'
    kms_policy=policy([allow('kms:*','*')|{'Principal':{'AWS':f'arn:aws:iam::{account}:root'}},allow(['kms:Encrypt','kms:Decrypt','kms:ReEncrypt*','kms:GenerateDataKey*','kms:Describe*'],'*')|{'Principal':{'Service':f'logs.{region}.amazonaws.com'},'Condition':{'ArnEquals':{'kms:EncryptionContext:aws:logs:arn':logarn}}}])
    once('logsKey','kms','create-key',lambda x:x['KeyMetadata']['Arn'],Description='Afterimage build logs',Policy=json.dumps(kms_policy),Tags=[{'TagKey':'Project','TagValue':'afterimage'}])
    call('logs','associate-kms-key',logGroupName=state['buildLogs'],kmsKeyId=state['logsKey'])
    role('executionRole','ecs-tasks.amazonaws.com',f'arn:aws:ecs:{region}:{account}:*')
    role('taskRole','ecs-tasks.amazonaws.com',f'arn:aws:ecs:{region}:{account}:*')
    role('infrastructureRole','ecs.amazonaws.com')
    role('buildRole','codebuild.amazonaws.com',f'arn:aws:codebuild:{region}:{account}:project/{prefix}')
    call('iam','attach-role-policy',RoleName=prefix+'-infrastructureRole',PolicyArn='arn:aws:iam::aws:policy/service-role/AmazonECSInfrastructureRoleforExpressGatewayServices')
    execution=[allow('ecr:GetAuthorizationToken','*'),allow(['ecr:BatchGetImage','ecr:GetDownloadUrlForLayer','ecr:BatchCheckLayerAvailability'],repoarn),allow(['logs:CreateLogStream','logs:PutLogEvents'],f'arn:aws:logs:{region}:{account}:log-group:{state["apiLogs"]}:*')]
    task=[allow(['dynamodb:GetItem','dynamodb:PutItem','dynamodb:DeleteItem','dynamodb:UpdateItem'],f'arn:aws:dynamodb:{region}:{account}:table/{prefix}')]
    build=[allow('ecr:GetAuthorizationToken','*'),allow(['ecr:BatchCheckLayerAvailability','ecr:InitiateLayerUpload','ecr:UploadLayerPart','ecr:CompleteLayerUpload','ecr:PutImage','ecr:BatchGetImage'],repoarn),allow(['s3:GetObject','s3:GetObjectVersion'],f'arn:aws:s3:::{bucket}/source/*'),allow('s3:GetBucketLocation',f'arn:aws:s3:::{bucket}'),allow(['logs:CreateLogStream','logs:PutLogEvents'],logarn+':*')]
    for label,statements in [('executionRole',execution),('taskRole',task),('buildRole',build)]:
        call('iam','put-role-policy',RoleName=prefix+'-'+label,PolicyName='AfterimageScopedAccess',PolicyDocument=json.dumps(policy(statements)))
    call('dynamodb','update-time-to-live',TableName=prefix,TimeToLiveSpecification={'Enabled':True,'AttributeName':'expires'}) if not state.get('ttl') else None
    state['ttl']=True;save()
    call('dynamodb','update-continuous-backups',TableName=prefix,PointInTimeRecoverySpecification={'PointInTimeRecoveryEnabled':True})
    print('Foundation ready:',prefix,flush=True)
