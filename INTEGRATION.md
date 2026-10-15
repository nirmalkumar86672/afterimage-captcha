# Give Afterimage to another website

Status: AWS private beta. The service origin is `https://af-e8a39971fdef485c8e772449c5d2a21d.ecs.ap-south-1.on.aws`. The approved renderer is unchanged. Your customer needs **both** the browser widget and backend verification.

## Customer frontend

Place inside the form:

```html
<div class="temporal-captcha"
     data-sitekey="SITE_KEY_FROM_OPERATOR"
     data-action="signup"></div>
<script src="https://af-e8a39971fdef485c8e772449c5d2a21d.ecs.ap-south-1.on.aws/widget.js" async></script>
```

The widget inserts an isolated iframe and a hidden field called `temporal-captcha-response`. It emits bubbling events:

- `captcha:verified`: `event.detail.token` and `event.detail.expiresIn`.
- `captcha:expired`: clear form readiness. Also emitted when a fresh challenge starts.

For normal form submissions, send the hidden field to your backend. For fetch-based forms, read it or listen to the event and include the token yourself. A token is valid for 120 seconds and can be redeemed only once. A network error after redemption may require a fresh challenge; redemption is deliberately not retry-idempotent.

If you create the container after script load, call `Afterimage.render(element)`. You can put multiple widgets on a page. Parent message handling checks both origin and iframe window. The service validates the site's allowed origins and emits an exact `frame-ancestors` policy. Your site's CSP must allow the service origin in `script-src` and `frame-src`; a sandboxed outer iframe also needs compatible policies.

## Customer backend (Python example)

Use environment variables for the secret and the fixed expected origin. Never take expected action/origin from the visitor's request; choose them from the server route being protected.

```python
import json, os
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError


def captcha_valid(token):
    payload = json.dumps({
        'token': token,
        'expectedAction': 'signup',
        'expectedOrigin': 'https://www.customer.example',
    }).encode()
    request = Request(
        'https://af-e8a39971fdef485c8e772449c5d2a21d.ecs.ap-south-1.on.aws/v1/siteverify',
        data=payload,
        headers={
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + os.environ['CAPTCHA_SECRET'],
        },
        method='POST',
    )
    try:
        with urlopen(request, timeout=5) as response:
            return json.load(response).get('success') is True
    except (HTTPError, URLError, TimeoutError, ValueError):
        return False
```

Call this **before** creating the account or sending the protected message. Reject or ask for a fresh challenge if verification fails. Browser success is not authorization. Do not rely on client-side button disabling. Keep normal session/CSRF checks and rate limits on the customer form: CAPTCHA does not replace them.

Successful response:

```json
{"success":true,"sitekey":"site_...","action":"signup","origin":"https://www.customer.example"}
```

Wrong tenant, origin, or action fails without consuming a valid token; successful redemption consumes it atomically. Expired/missing/replayed tokens fail. A wrong challenge answer consumes that challenge. Secrets are only accepted via `Authorization`, never query strings. No browser CORS access to the verification endpoint is provided.

## Run the working local customer example

From the `temporal-captcha` directory:

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements-service.txt
.venv/bin/python -m service.manage \
  --name 'Local integration demo' \
  --origin http://127.0.0.1:8081 \
  --hourly-limit 100 \
  --output .local/customer.json
ENABLE_DEMO=1 .venv/bin/gunicorn --bind 127.0.0.1:8081 --workers 2 'service.app:create_app()'
```

Provisioning was already run in this workspace; do not repeat it with the same output path. Open http://127.0.0.1:8081, solve the widget, then submit the protected sample form. The backend reads the private secret file; `/demo/config` exposes only the site key. The sample makes no accounts and sends no email. `APP_ENV=production` disables local demo redemption even if `ENABLE_DEMO=1` is set. `PUBLIC_DEMO_SITEKEY` optionally enables a public widget preview that exposes only the public site key and never performs backend demo redemption.

Local state is SQLite in `.local/service.db`; AWS state uses the DynamoDB table in `DYNAMODB_TABLE`. Local secrets/state are gitignored and omitted from the Docker build. The original research UI remains separately available via `python3 server.py` on port 8080.
