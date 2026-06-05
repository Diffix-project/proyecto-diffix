"""
Integración con Cloudflare R2 (compatible con S3 API, via boto3).

Interfaz pública:
  upload_bytes(key, data, content_type) -> str
  generate_presigned_url(key, expires_in=3600) -> str

En modo mock no realiza ninguna llamada de red.
En modo real usa el cliente boto3 configurado con las credenciales R2.
"""

import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


def _get_client():  # type: ignore[return]
    """Construye el cliente boto3 para R2. Solo se llama en modo real."""
    try:
        import boto3

        return boto3.client(
            "s3",
            endpoint_url=settings.r2_endpoint
            or f"https://{settings.r2_account_id}.r2.cloudflarestorage.com",
            aws_access_key_id=settings.r2_access_key_id,
            aws_secret_access_key=settings.r2_secret_access_key,
            region_name="auto",
        )
    except Exception as exc:  # noqa: BLE001
        logger.error("storage: error construyendo cliente R2: %s", exc)
        raise


def upload_bytes(key: str, data: bytes, content_type: str) -> str:
    """
    Sube datos a R2 y devuelve la key (que sirve como identificador del objeto).

    Mock: devuelve 'mock://r2/{key}' sin realizar ninguna llamada de red.
    Real: sube al bucket configurado en settings.r2_bucket.
    """
    if settings.use_mocks:
        logger.debug("storage [mock] upload_bytes key=%s (%d bytes)", key, len(data))
        return f"mock://r2/{key}"

    # Real: fase Scout
    client = _get_client()
    client.put_object(
        Bucket=settings.r2_bucket,
        Key=key,
        Body=data,
        ContentType=content_type,
    )
    logger.info("storage upload_bytes key=%s (%d bytes)", key, len(data))
    return key


def generate_presigned_url(key: str, expires_in: int = 3600) -> str:
    """
    Genera una URL firmada para acceso privado al objeto.

    Mock: devuelve 'mock://r2/{key}?signed=1'.
    Real: genera URL firmada con boto3 (expiración en segundos).
    """
    if settings.use_mocks:
        logger.debug("storage [mock] generate_presigned_url key=%s", key)
        return f"mock://r2/{key}?signed=1"

    # Real: fase Scout
    client = _get_client()
    url: str = client.generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.r2_bucket, "Key": key},
        ExpiresIn=expires_in,
    )
    logger.info("storage generate_presigned_url key=%s expires_in=%d", key, expires_in)
    return url
