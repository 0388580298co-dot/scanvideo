# Publishing

ScanVideo publishes only through official platform APIs.

## YouTube

1. Enable YouTube Data API v3 in Google Cloud.
2. Create a Web OAuth client and register:
   `http://localhost:8000/api/v1/oauth/youtube/callback`
3. Place the downloaded OAuth client JSON at the configured `YOUTUBE_CLIENT_SECRETS_FILE` path.
4. Open `/api/v1/oauth/youtube/start` in a browser.
5. Complete Google consent.
6. ScanVideo stores the resulting token outside the repository.
7. A platform account is created automatically.

The publisher uses `videos.insert` with OAuth scope `youtube.upload` and defaults to private visibility.

## TikTok

1. Register an app in TikTok for Developers.
2. Enable Login Kit and Content Posting API.
3. Register the exact redirect URI from `TIKTOK_REDIRECT_URI`.
4. Request the required posting scope and obtain approval where TikTok requires it.
5. Set the client key and secret in `.env`.
6. Open `/api/v1/oauth/tiktok/start`.
7. Complete consent.
8. Tokens are stored outside the repository and a platform account is created.

The Direct Post adapter uses TikTok's official creator-info and video-init/upload flow. It does not use browser automation, cookies, or session hijacking.

## Scheduling

Create a schedule with:

```json
{
  "job_id": "JOB_ID",
  "platform": "youtube",
  "scheduled_at": "2026-09-15T19:00:00+07:00"
}
```

If title/description are omitted, ScanVideo uses the generated content package. Celery Beat dispatches due posts every 30 seconds.

## Important platform limitations

Platform approval, quota, audits and visibility restrictions are controlled by the platforms. ScanVideo does not attempt to bypass them.
