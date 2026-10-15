"""Operator-only provisioning. AWS uses your CLI/SSO credential chain."""
import argparse,json,os
from pathlib import Path
from service.store import configured_store
from service.core import CaptchaService

def main():
    p=argparse.ArgumentParser();p.add_argument('--name',required=True);p.add_argument('--origin',action='append',required=True);p.add_argument('--hourly-limit',type=int,default=100);p.add_argument('--output',required=True)
    a=p.parse_args();out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True)
    # Reserve a private output file before creating keys; never overwrite credentials.
    fd=os.open(out,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    try:
        service=CaptchaService(configured_store(),local=os.getenv('APP_ENV')!='production')
        value=service.create_site(a.name,a.origin,a.hourly_limit)
        with os.fdopen(fd,'w') as f:json.dump(value,f,indent=2)
    except Exception:
        try:os.close(fd)
        except OSError:pass
        out.unlink(missing_ok=True);raise
    print('Created site:',value['sitekey']);print('Secret saved privately to',out)
if __name__=='__main__':main()
