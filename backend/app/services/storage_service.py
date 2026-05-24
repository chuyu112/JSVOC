import mimetypes
import time
import uuid

from app.core.config import Settings, get_settings


def is_oss_configured(settings: Settings | None = None) -> bool:
    settings = settings or get_settings()
    return all(
        [
            settings.oss_access_key_id.strip(),
            settings.oss_access_key_secret.strip(),
            settings.oss_endpoint.strip(),
            settings.oss_bucket_name.strip(),
        ]
    )


def build_generated_image_object_key(
    *,
    user_id: int,
    project_id: int | None,
    mime_type: str,
) -> str:
    extension = guess_extension(mime_type) or ".png"
    date_prefix = time.strftime("%Y/%m/%d", time.gmtime())
    project_part = f"projects/{project_id}" if project_id is not None else "account"
    return f"users/{user_id}/{project_part}/images/{date_prefix}/{uuid.uuid4().hex}{extension}"


def build_generated_video_object_key(
    *,
    user_id: int,
    project_id: int | None,
    mime_type: str,
) -> str:
    extension = guess_extension(mime_type) or ".mp4"
    date_prefix = time.strftime("%Y/%m/%d", time.gmtime())
    project_part = f"projects/{project_id}" if project_id is not None else "account"
    return f"users/{user_id}/{project_part}/videos/{date_prefix}/{uuid.uuid4().hex}{extension}"


def build_reference_media_object_key(
    *,
    user_id: int,
    project_id: int | None,
    media_kind: str,
    mime_type: str,
) -> str:
    extension = guess_extension(mime_type) or ".bin"
    date_prefix = time.strftime("%Y/%m/%d", time.gmtime())
    project_part = f"projects/{project_id}" if project_id is not None else "account"
    safe_kind = media_kind if media_kind in {"images", "videos", "audios"} else "files"
    return f"users/{user_id}/{project_part}/references/{safe_kind}/{date_prefix}/{uuid.uuid4().hex}{extension}"


def upload_bytes(
    *,
    object_key: str,
    content: bytes,
    content_type: str,
    settings: Settings | None = None,
) -> str:
    settings = settings or get_settings()
    import oss2

    auth = oss2.Auth(settings.oss_access_key_id, settings.oss_access_key_secret)
    bucket = oss2.Bucket(auth, normalized_endpoint(settings.oss_endpoint), settings.oss_bucket_name)
    bucket.put_object(object_key, content, headers={"Content-Type": content_type})
    return object_key


def sign_get_url(
    object_key: str,
    *,
    settings: Settings | None = None,
) -> tuple[str, int]:
    settings = settings or get_settings()
    import oss2

    auth = oss2.Auth(settings.oss_access_key_id, settings.oss_access_key_secret)
    bucket = oss2.Bucket(auth, normalized_endpoint(settings.oss_endpoint), settings.oss_bucket_name)
    expires_in = settings.oss_url_expire_seconds
    signed_url = bucket.sign_url("GET", object_key, expires_in, slash_safe=True)
    return signed_url, int(time.time()) + expires_in


def normalized_endpoint(endpoint: str) -> str:
    cleaned = endpoint.strip()
    if cleaned.startswith("http://") or cleaned.startswith("https://"):
        return cleaned
    return f"https://{cleaned}"


def guess_extension(mime_type: str) -> str:
    guessed = mimetypes.guess_extension(mime_type.strip().lower() or "image/png")
    return guessed or ".png"
