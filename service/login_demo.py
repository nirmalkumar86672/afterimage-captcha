"""Demo login hosted alongside the CAPTCHA, with server-side token redemption."""
import os
from pathlib import Path
from flask import Blueprint, render_template_string, request, session, jsonify, redirect
from werkzeug.security import generate_password_hash, check_password_hash

def install(app, service):
    origin=os.getenv('LOGIN_DEMO_ORIGIN')
    if not origin:return
    config=service.store.get('internal:login-demo')
    if not config:raise RuntimeError('Hosted login demo configuration missing')
    app.secret_key=config['sessionKey']
    app.config.update(SESSION_COOKIE_NAME='afterimage_demo',SESSION_COOKIE_SECURE=True,
                      SESSION_COOKIE_HTTPONLY=True,SESSION_COOKIE_SAMESITE='Lax',
                      SESSION_COOKIE_PATH='/login-demo')
    bp=Blueprint('login_demo',__name__,url_prefix='/login-demo')
    password_hash=generate_password_hash('DemoPass123!')
    template=(Path(__file__).parent/'static/login-demo.html').read_text()
    @bp.get('/')
    def index():
        return render_template_string(template,sitekey=config['sitekey'],service=origin,logged_in=session.get('logged_in',False))
    @bp.post('/login')
    def login():
        if request.headers.get('Origin')!=origin:return jsonify(error='Invalid request origin.'),403
        data=request.get_json(silent=True)
        if not isinstance(data,dict):return jsonify(error='Invalid request.'),400
        token=data.get('token')
        if not isinstance(token,str) or not 1<=len(token)<=256:return jsonify(error='Complete the CAPTCHA first.'),400
        result=service.redeem(config['secret'],token,'login',origin)
        if not result['success']:return jsonify(error='CAPTCHA expired or already used. Try a new challenge.'),400
        password=data.get('password')
        if data.get('email')!='demo@example.com' or not isinstance(password,str) or not check_password_hash(password_hash,password):
            return jsonify(error='Incorrect demo credentials. Complete a new challenge and retry.'),401
        session.clear();session['logged_in']=True
        return jsonify(success=True)
    @bp.post('/logout')
    def logout():
        # Browser form POSTs may send Origin: null under Referrer-Policy: no-referrer.
        # Fetch Metadata still identifies same-origin navigation; never trust cross-site POSTs.
        supplied=request.headers.get('Origin')
        if supplied!=origin and not (supplied in (None,'null') and request.headers.get('Sec-Fetch-Site')=='same-origin'):
            return 'Invalid origin',403
        session.clear();return redirect('/login-demo/')
    @bp.after_request
    def headers(response):
        response.headers['Content-Security-Policy']="default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; frame-src 'self'; frame-ancestors 'none'; form-action 'self'"
        return response
    app.register_blueprint(bp)
