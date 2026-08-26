# MSG91 phone match fix v79

- Fixes valid OTP login being rejected with “Verified mobile number does not match the login number”.
- Normalizes MSG91 verified identifiers by comparing the canonical last 10 digits, so `7013039172`, `917013039172`, and `+917013039172` match correctly.
- Keeps server-side binding between the verified MSG91 token and the phone submitted for login.
- Bumps frontend cache version to v79.
