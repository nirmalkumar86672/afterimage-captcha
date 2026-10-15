# AWS beta deployment

Region: Mumbai (`ap-south-1`). AWS CLI profile: `afterimage`.

Public preview: https://af-e8a39971fdef485c8e772449c5d2a21d.ecs.ap-south-1.on.aws

The root page demonstrates the live widget. It does not create accounts. Customer applications must redeem tokens on their own backend. See [INTEGRATION.md](../INTEGRATION.md) for the embed and verification example.

## Hosted login demonstration

The Stillroom demo is mounted at `/login-demo/` on this same service. Demo account: `demo@example.com` / `DemoPass123!`. It checks a single-use CAPTCHA token on the backend before creating a secure session. This is a demonstration identity only. The configuration is stored in the internal DynamoDB record `internal:login-demo`; only the public site key is sent to the browser.

## Resources and operation

Dedicated resource prefix: `afterimage-beta-53cb5c`. Resource IDs, image digest and deployment state are recorded in `.local/aws-deployment.json` (relative to the project root).

- ECS Express Gateway service in cluster `default`, using the default VPC; HTTPS certificate and load balancer managed by Express.
- Fargate: 1 vCPU / 2 GiB per task, minimum 1, maximum 2, CPU scaling target 60%.
- DynamoDB on-demand table with encryption, point-in-time recovery and TTL. Application checks expiry immediately; TTL cleanup is asynchronous.
- Immutable ECR repository; CodeBuild performs the Linux container build and renderer import/render check.
- Private encrypted S3 build-source bucket; source objects expire after seven days.
- Application and build log groups retained for 14 days; build logs use a dedicated KMS key.
- Scoped execution, application and build IAM roles; AWS managed Express infrastructure role policy.
- WAF IP rate rule: 300 requests per five-minute window, including backend verification requests. Tune for customer servers and shared NATs before increasing traffic. Request sampling is disabled.

These resources incur recurring AWS charges even without visitors. The task maximum does not cap other resource charges. No billing budget or alert notification destination is configured.

Run `python3 deploy/status-express.py` from the project directory to inspect deployment metadata. ACTIVE alone does not prove readiness: check `/healthz` and ECS task health as well. Deployment was performed via CLI scripts, not CloudFormation; deleting a CloudFormation stack will not remove these resources. Do not rerun `start-express.py` to update the existing service. For a release, run `build-express.py`, wait for CodeBuild success, resolve its new image digest, then use `ecs update-express-gateway-service` with the existing service ARN and complete primary-container settings. Preserve the previous digest for rollback.

## Onboard another website

From the `temporal-captcha` directory, register each customer's exact HTTPS origin and create a separate key pair:

```sh
AWS_PROFILE=afterimage AWS_REGION=ap-south-1 APP_ENV=production \
DYNAMODB_TABLE=afterimage-beta-53cb5c \
.venv/bin/python -m service.manage \
  --name 'Example customer' \
  --origin https://www.customer.example \
  --hourly-limit 100 \
  --output .local/example-customer.secret.json
```

This command uses AWS operator credentials. Do not expose it as an unauthenticated HTTP endpoint. Each output file is mode 0600 and must have a new filename. Give the customer their public site key for HTML and their secret through a private channel for backend verification. Do not share the demo keys among customers. Public signup, billing, ownership verification, key rotation and a management dashboard are not implemented.

The public preview has a quota of 100 new challenges per hour. Its credentials are saved privately in `.local/customer-production.secret.json`; the secret is never embedded in the browser or source archive.

## Verified on deployment

ECS reached steady state with one running task. Live HTTPS checks passed for the page, widget script, challenge creation/PNG delivery, origin rejection, answer submission, action binding, successful backend verification and replay rejection. Production demo redemption returns 404. Browser inspection confirmed the animated widget loaded. Local suite: 14 passing tests; cloud Linux container renderer/import check passed.

## Beta limitations

This is a perception experiment, not established bot resistance or screenshot protection. The 32-word list permits guessing and multiple frames can reveal motion. Human completion rates, accessibility alternatives and load capacity need validation before commercial rollout.

The first ECR base-image scan reported four HIGH and one MEDIUM findings in Debian packages (gcc-14/libstdc++, pcre2, zlib and dash). No exploitability claim is made; review and patch these before general availability. The service does not accept user regexes, filenames or file uploads. Keep image scanning and dependency updates part of releases.

Hosted login release (14 October 2026): live `/login-demo/` checks passed for missing-token rejection, valid login, Secure/HttpOnly session cookies, repeated authenticated requests, token replay rejection and logout. All 15 local tests passed. Chrome inspection confirmed the page and animated CAPTCHA load. The release reused the existing service and load balancer.
