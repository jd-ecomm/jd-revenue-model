# JD Sports Canada · Predictive Revenue Model

Password-protected snapshot of the Predictive Revenue Model dashboard, served with GitHub Pages.

- `index.html` is encrypted with [StatiCrypt](https://github.com/robinmoisson/staticrypt) (AES-256, PBKDF2). The data cannot be read without the team password.
- `.staticrypt.json` holds the public salt so "Remember me" keeps working between updates. It is not secret.
- `kit.tar.gz.enc` is the encrypted set of inputs (AES-256, same password).
- Rebuilt Monday to Friday at 9:39 Vancouver from the live Claude dashboard; see `tools/RUNBOOK.md`. Do not edit `index.html` by hand.
