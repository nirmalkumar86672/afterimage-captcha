# Local login customer example

Open http://127.0.0.1:8082 (use this exact origin, not localhost).

Demo email: `demo@example.com`; demo password: `DemoPass123!`.

The local page embeds the live AWS widget. Its local Flask backend calls AWS `/v1/siteverify` with the private customer secret, fixed action `login` and fixed origin before checking credentials and creating an HttpOnly session cookie. Each CAPTCHA token is single-use. Refresh the challenge after a failed login. The account is demonstration-only; no real user database exists. Session signing keys reset when the process restarts.

Run from the project root:

```sh
.venv/bin/python login-demo/app.py
```

The server binds only to loopback. Credentials are in `.local/login-demo.secret.json`, mode 0600, excluded from Git and the AWS image. A dedicated AWS site registration allows this exact loopback HTTP origin for development; customer production origins must use HTTPS. Quota: 100 challenges/hour.

Verified over HTTP: missing CAPTCHA rejection, live AWS challenge/verification, authenticated session, replay rejection and logout. Browser checked for successful remote iframe loading. This demo is not a production identity system.

## Hosted version

The same demo is packaged as `service/login_demo.py` and `service/static/login-demo.html`, mounted at `/login-demo/` on the existing AWS service. It uses the same server-side single-use verification logic as the public API, with action `login` and the fixed deployed origin. The backend obtains its CAPTCHA secret and shared session-signing key from an internal DynamoDB record; neither is shipped in browser assets or the image. Secure, HttpOnly session cookies are limited to `/login-demo`.

Release: run `deploy/build-express.py`, wait for a successful CodeBuild, then run `deploy/enable-login-demo.py`. The latter saves the previous image for rollback, provisions internal configuration if absent, and updates the existing service. It does not create an additional Fargate service or load balancer. Keep the demo account separate from any real identity system.
