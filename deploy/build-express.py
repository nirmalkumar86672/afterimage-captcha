"""Package only application files and run a Linux image build in AWS CodeBuild."""
import json,zipfile,time,subprocess
from pathlib import Path
from importlib.util import spec_from_file_location,module_from_spec
spec=spec_from_file_location('prepare',Path(__file__).with_name('prepare-express.py'));prepare=module_from_spec(spec);spec.loader.exec_module(prepare)
call,state,save,ROOT=prepare.call,prepare.state,prepare.save,prepare.ROOT
if __name__=='__main__':
    prefix=state['prefix'];repository=state['repository'];region=state['region'];bucket=state['bucket']
    tag='release-'+time.strftime('%Y%m%d%H%M%S',time.gmtime());state['imageTag']=tag;state['imageUri']=repository+':'+tag;save()
    buildspec={'version':'0.2','phases':{'pre_build':{'commands':['docker info',f'aws ecr get-login-password --region {region} | docker login --username AWS --password-stdin {repository.split("/")[0]}']},'build':{'commands':[f'docker build --platform linux/amd64 -t {repository}:{tag} .','docker run --rm --entrypoint python '+repository+':'+tag+' -c "import server; assert len(server.render(\'star\')) > 1000; from service.app import create_app; print(\'Container import and renderer check passed\')"',f'docker push {repository}:{tag}']}}}
    archive=ROOT/'.local/source.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        files=[ROOT/n for n in ['Dockerfile','.dockerignore','requirements-service.txt','server.py']]
        files+=list((ROOT/'static').glob('*'))
        files+=list((ROOT/'service').glob('*.py'))
        files+=list((ROOT/'service/static').glob('*'))
        for f in files:
            if f.is_file() and not f.name.startswith('test_'):z.write(f,str(f.relative_to(ROOT)))
        z.writestr('buildspec.yml',json.dumps(buildspec))
    source='source/'+tag+'.zip'
    subprocess.run([prepare.AWS,'s3','cp',str(archive),'s3://'+bucket+'/'+source,'--sse','AES256','--profile',state['profile'],'--region',region,'--only-show-errors'],check=True)
    project=dict(name=prefix,source={'type':'S3','location':bucket+'/'+source},artifacts={'type':'NO_ARTIFACTS'},environment={'type':'LINUX_CONTAINER','computeType':'BUILD_GENERAL1_SMALL','image':'aws/codebuild/standard:7.0','privilegedMode':True},serviceRole=state['buildRole'],timeoutInMinutes=20,queuedTimeoutInMinutes=10,logsConfig={'cloudWatchLogs':{'status':'ENABLED','groupName':state['buildLogs']}},tags=[{'key':'Project','value':'afterimage'}])
    if not state.get('project'):
        call('codebuild','create-project',**project);state['project']=prefix;save()
    else:call('codebuild','update-project',**project)
    result=call('codebuild','start-build',projectName=prefix)
    state['buildId']=result['build']['id'];save()
    print('Build started:',state['buildId']);print('Source archive bytes:',archive.stat().st_size)
