# MSG91 initialization fix v77

- Added required top-level MSG91 Widget `success` and `failure` callbacks.
- Waits until `window.sendOtp` and `window.verifyOtp` are actually exposed before marking OTP ready.
- Bumped frontend asset cache version to v77.
