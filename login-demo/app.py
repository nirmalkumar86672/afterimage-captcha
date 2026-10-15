"""Local customer website; CAPTCHA verification goes to the deployed AWS service."""
import json, secrets
from pathlib import Path
from urllib.request import Request, urlopen
from flask import Flask, render_template, request, session, jsonify, redirect
from werkzeug.security import generate_password_hash, check_password_hash
ROOT=Path(__file__).resolve().parents[1]
config=json.loads((ROOT/'.local/login-demo.secret.json').read_text())
ORIGIN='http://127.0.0.1:8082'
SERVICE=config['service']
app=Flask(__name__)
app.secret_key=secrets.token_bytes(32)
app.config.update(MAX_CONTENT_LENGTH=8192,SESSION_COOKIE_HTTPONLY=True,SESSION_COOKIE_SAMESITE='Lax')
password_hash=generate_password_hash('DemoPass123!')
@app.get('/')
def index():
    return render_template('login.html',sitekey=config['sitekey'],service=SERVICE,logged_in=session.get('logged_in',False))
@app.post('/login')
def login():
    if request.headers.get('Origin')!=ORIGIN:return jsonify(error='Invalid request origin.'),403
    data=request.get_json(silent=True) or {}
    token=data.get('token')
    if not isinstance(token,str) or not 1<=len(token)<=256:return jsonify(error='Complete the CAPTCHA first.'),400
    payload=json.dumps(dict(token=token,expectedAction='login',expectedOrigin=ORIGIN)).encode()
    req=Request(SERVICE+'/v1/siteverify',data=payload,headers={'Content-Type':'application/json','Authorization':'Bearer '+config['secret']})
    try:
        with urlopen(req,timeout=10) as response:verified=json.load(response).get('success') is True
    except Exception:return jsonify(error='Verification is unavailable. Try a new challenge.'),503
    if not verified:return jsonify(error='CAPTCHA expired or already used. Try a new challenge.'),400
    email=data.get('email');password=data.get('password')
    if email!='demo@example.com' or not isinstance(password,str) or not check_password_hash(password_hash,password):
        return jsonify(error='Incorrect demo credentials. Complete a new challenge and retry.'),401
    session.clear();session['logged_in']=True
    return jsonify(success=True)
@app.post('/logout')
def logout():
    if request.headers.get('Origin')!=ORIGIN:return 'Invalid origin',403
    session.clear();return redirect('/')
@app.after_request
def headers(r):
    r.headers['Cache-Control']='no-store'
    r.headers['X-Content-Type-Options']='nosniff'
    r.headers['Content-Security-Policy']=f"default-src 'self'; script-src 'self' 'unsafe-inline' {SERVICE}; style-src 'self' 'unsafe-inline'; frame-src {SERVICE}; frame-ancestors 'none'; form-action 'self'"
    return r
if __name__=='__main__':app.run(host='127.0.0.1',port=8082,debug=False)
