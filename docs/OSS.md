# OSS Configuration

JSVOC stores generated images, generated videos, and uploaded reference media in Alibaba Cloud OSS.

## Production Settings

Current production bucket:

```env
OSS_ENDPOINT=oss-cn-beijing.aliyuncs.com
OSS_BUCKET_NAME=jsvoc2
OSS_URL_EXPIRE_SECONDS=600
```

`OSS_ACCESS_KEY_ID` and `OSS_ACCESS_KEY_SECRET` are configured only on the server:

```text
/opt/JSVOC/current/.env
```

Do not commit real AccessKey values to Git. Keep `.env.example` and docs as placeholders only.

## Required Permissions

The RAM user behind the AccessKey must have object permissions on bucket `jsvoc2`.

Minimum operations used by the app and verification scripts:

```text
oss:PutObject
oss:GetObject
oss:DeleteObject
```

If the app must list objects in future tooling, also grant the appropriate list permission for the bucket.

## Runtime Usage

The backend reads these values from `app.core.config.Settings`:

```env
OSS_ACCESS_KEY_ID=
OSS_ACCESS_KEY_SECRET=
OSS_ENDPOINT=
OSS_BUCKET_NAME=
OSS_URL_EXPIRE_SECONDS=600
```

OSS is used by:

- generated image persistence
- generated video persistence
- uploaded reference media for video generation
- signed temporary URLs returned to the frontend

After changing OSS variables, recreate the backend container so it reloads `.env`:

```bash
cd /opt/JSVOC/current
docker compose -p jsvoc up -d --force-recreate backend
curl -fsS http://127.0.0.1:8000/health
```

## Endpoint Note

Use the endpoint shown by the OSS console for the bucket. On 2026-05-24, bucket `jsvoc2` returned the required endpoint `oss-cn-beijing.aliyuncs.com` during verification. If the bucket is recreated in Heyuan later, update `OSS_ENDPOINT` to the new bucket endpoint, for example `oss-cn-heyuan.aliyuncs.com`, and restart the backend.
