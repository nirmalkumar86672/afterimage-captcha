# Afterimage — local temporal CAPTCHA experiment

Run `python3 -m venv .venv`, activate it, install `pip install -r requirements.txt`, then run `python3 server.py`. Open http://127.0.0.1:8080. Run tests with `python3 -m unittest -v`.

## Current experiment

A dark strip with pale dots contains three object names defined by sideways-moving grain against stationary grain, with identical color distributions. Select the matching illustrations in the 3×3 grid, left-to-right according to the instruction. Selected tiles show their sequence number; click a selected tile to remove it or use Undo last. Verification consumes the challenge on the first attempt and expires it after two minutes.

The server generates a 48-frame PNG atlas, randomized option order and opaque option IDs. Only the rasterized instruction, public options, and metadata reach the browser. The required order remains in server memory. This visually approximates the supplied reference; it does not reproduce its unknown implementation. Original SVG illustrations are used instead of the reference photographs.

## Limits

The text has no intentional static brightness difference from the background. Temporal motion analysis can still recover it. It is not proven bot-resistant, screenshot-proof, or production-ready. Single frames may reveal some or all letters. Nine choices with three distinct ordered selections give 504 possible sequences, so blind guessing succeeds about 0.2% of the time. The entire animation is available to a solver. Playback respects reduced-motion preferences, but a non-motion accessible alternative is still needed.

The local development server, in-memory state, and generation throttle are not production infrastructure. No tenant authentication, reusable verification tokens, AWS deployment, or third-party embed integration is included. Before deployment, test human usability and automated reconstruction, then add authenticated verification, atomic single-use storage, tenant-bound tokens, abuse controls, and an accessible alternative.
