import base64,json,os
from pathlib import Path
from flask import Flask,request,jsonify,send_from_directory,make_response
from werkzeug.exceptions import HTTPException
from service.store import configured_store
from service.core import CaptchaService,ServiceError

ASSETS=Path(__file__).parent/'static'
BASE=Path(__file__).resolve().parents[1]

def create_app(store=None):
    app=Flask(__name__,static_folder=None)
    app.config['MAX_CONTENT_LENGTH']=4096
    production=os.getenv('APP_ENV')=='production'
    service=CaptchaService(store or configured_store(),local=not production)
    app.extensions['captcha']=service
    def body():
        value=request.get_json(silent=True)
        if not isinstance(value,dict):raise ServiceError('JSON object required')
        return value
    def field(data,name,maxlen=256):
        value=data.get(name)
        if not isinstance(value,str) or not value or len(value)>maxlen:raise ServiceError('Invalid '+name)
        return value
    @app.errorhandler(ServiceError)
    def service_error(e):return jsonify(error=e.message),e.status
    @app.errorhandler(HTTPException)
    def http_error(e):return jsonify(error=e.name),e.code
    @app.after_request
    def headers(response):
        response.headers['Cache-Control']='no-store'
        response.headers['X-Content-Type-Options']='nosniff'
        response.headers['Referrer-Policy']='no-referrer'
        if 'Content-Security-Policy' not in response.headers:
            response.headers['Content-Security-Policy']="default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self'; frame-src 'self'; frame-ancestors 'none'"
        if production:response.headers['Strict-Transport-Security']='max-age=31536000'
        return response
    @app.get('/healthz')
    def health():return jsonify(status='ok')
    @app.get('/widget.js')
    def widget():return send_from_directory(ASSETS,'widget.js')
    @app.get('/assets/<name>')
    def assets(name):
        if name=='style.css':return send_from_directory(BASE/'static',name)
        if name not in ('frame.js','frame.css','demo.js','demo.css'):raise ServiceError('Not found',404)
        return send_from_directory(ASSETS,name)
    @app.get('/frame')
    def frame():
        key=field(request.args,'sitekey');parent=field(request.args,'parent')
        service.site(key,parent)
        response=make_response(send_from_directory(ASSETS,'frame.html'))
        response.headers['Content-Security-Policy']=f"default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self'; frame-ancestors {parent}"
        return response
    @app.post('/v1/challenges')
    def challenges():
        data=body();return jsonify(service.issue(field(data,'sitekey'),field(data,'parent'),field(data,'action',48)))
    @app.get('/v1/images/<ident>')
    def images(ident):
        image=service.store.get('image:'+ident)
        if not image:raise ServiceError('Image expired',404)
        return app.response_class(base64.b64decode(image['data']),mimetype='image/png')
    @app.post('/v1/solve')
    def solve():
        data=body();return jsonify(service.solve(field(data,'id'),field(data,'answer',32)))
    @app.post('/v1/siteverify')
    def verify():
        data=body();auth=request.headers.get('Authorization','')
        if not auth.startswith('Bearer ') or len(auth)>256:raise ServiceError('Secret key required',401)
        return jsonify(service.redeem(auth[7:],field(data,'token'),field(data,'expectedAction',48),field(data,'expectedOrigin')))
    # Local-only sample customer backend. Secret never reaches demo HTML/JavaScript.
    def demo_credentials():
        if production or os.getenv('ENABLE_DEMO')!='1':raise ServiceError('Not found',404)
        return json.loads((BASE/'.local/customer.json').read_text())
    @app.get('/')
    def demo():
        if not os.getenv('PUBLIC_DEMO_SITEKEY'):demo_credentials()
        return send_from_directory(ASSETS,'demo.html')
    @app.get('/demo/config')
    def demo_config():
        public=os.getenv('PUBLIC_DEMO_SITEKEY')
        if public:return jsonify(sitekey=public,previewOnly=True)
        return jsonify(sitekey=demo_credentials()['sitekey'],previewOnly=False)
    @app.post('/demo/submit')
    def demo_submit():
        credentials=demo_credentials();data=body()
        result=service.redeem(credentials['secret'],field(data,'token'),'signup',credentials['origins'][0])
        return jsonify(result),200 if result['success'] else 400
    from service.login_demo import install
    install(app,service)
    return app
