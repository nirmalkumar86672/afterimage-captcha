# Afterimage — original word prototype

Run `pip install -r requirements.txt` and `python3 server.py`, then visit http://127.0.0.1:8080. Test with `python3 -m unittest -v`.

Restored the earlier single-word version: 384×240 canvas, 3-pixel pale dots on a dark background, horizontal foreground motion and vertical background motion, 48 frames at 24 FPS, and a typed four-letter answer. The original large text mask and dot density are restored. The server generates frames and keeps the answer, consumes the first submission, and expires challenges after two minutes. Matching ignores case and surrounding whitespace.

The ordered-grid version is preserved in `versions/ordered-grid/` for later work.

This remains a local perception experiment. Single-frame ambiguity is not proven security; multi-frame motion analysis can reveal the word. The 32-word list permits blind guessing at 1/32. General availability still needs accessibility alternatives, stronger challenge design, customer account management, and load testing. See `deploy/LIVE.md` for the AWS beta deployment.

## Embeddable service and AWS private beta

The `service/` package adds an iframe widget, operator-issued public/secret keys, exact-origin registration, hourly issuance quotas, persisted challenges, and atomic single-use token redemption bound to customer/origin/action. The visual renderer above is reused unchanged.

- Customer integration and local demo: [INTEGRATION.md](INTEGRATION.md)
- Mumbai deployment and prerequisites: [deploy/README.md](deploy/README.md)
- AWS CloudFormation: [deploy/aws-stack.json](deploy/aws-stack.json)

The service has been provisioned on ECS Express Gateway in Mumbai. Public signup, billing, accessible alternatives, and a key-management dashboard are not implemented.

Validation: 14 tests pass across the prototype, local service, and mocked DynamoDB adapter; CloudFormation passes `cfn-lint` for `ap-south-1`. A live local HTTP smoke test exercises actual image generation, solving a test challenge from stored fixture state, and customer-backend token redemption. The browser widget layout loads without console errors. Live AWS checks also passed for challenge creation, image delivery, backend verification and replay rejection; ECS reached steady state with one task. These checks do not establish bot resistance or load capacity.

To reproduce checks:

```sh
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m pytest test_server.py service/test_service.py service/test_dynamo.py -q
.venv/bin/cfn-lint deploy/aws-stack.json --regions ap-south-1
```
