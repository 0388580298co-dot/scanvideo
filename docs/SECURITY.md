# Security

ScanVideo is designed for content the operator has permission to download, transform, and publish.

## Secrets

Never commit `.env`, OAuth tokens, client secrets, private keys, cookies, or passwords. CI does not require publishing credentials.

## Platform access

YouTube and TikTok integrations must use their official OAuth/API flows. The project does not implement CAPTCHA bypass, DRM bypass, anti-bot evasion, cookie/session theft, private-content extraction, or rate-limit bypass.

## Media inputs

Source URLs are validated as HTTP(S) input. Downloads are executed without playlists by default and have bounded subprocess timeouts. Media is validated with ffprobe before downstream processing.

## Publishing

Publishing must be an explicit, authorized operation. Keep the default YouTube visibility private until the account and workflow have been verified.
