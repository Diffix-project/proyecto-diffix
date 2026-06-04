"""
Integración con Apify para obtener job postings.

Interfaz pública:
  get_job_postings(company_name, since_days=30) -> list[dict]

Nunca scrapear LinkedIn directamente; siempre usar Apify.

En modo mock devuelve lista de ejemplo.
En modo real usa la API de Apify (stub para fase Scout).
"""

import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

_MOCK_JOB_POSTINGS: list[dict] = [
    {
        "title": "Desarrollador Backend Python",
        "company": "Empresa Ejemplo",
        "location": "Buenos Aires, AR",
        "posted_at": "2026-05-28",
        "url": "https://www.linkedin.com/jobs/view/mock-1",
        "description": "Buscamos desarrollador Python con experiencia en FastAPI y PostgreSQL.",
    },
    {
        "title": "Jefe de Ventas Zona Norte",
        "company": "Empresa Ejemplo",
        "location": "Buenos Aires, AR",
        "posted_at": "2026-05-30",
        "url": "https://www.linkedin.com/jobs/view/mock-2",
        "description": "Responsable de expandir cartera de clientes en zona norte GBA.",
    },
]


def get_job_postings(company_name: str, since_days: int = 30) -> list[dict]:
    """
    Devuelve publicaciones de empleo de la empresa en los últimos `since_days` días.

    Mock: lista de ejemplo sin llamada de red.
    Real: TODO — implementar en fase Scout usando el actor de Apify para LinkedIn Jobs.
    """
    if settings.use_mocks:
        logger.debug(
            "apify [mock] get_job_postings company=%s since_days=%d", company_name, since_days
        )
        return [dict(p, company=company_name) for p in _MOCK_JOB_POSTINGS]

    # Real: fase Scout
    # TODO (fase Scout): llamar a la API de Apify:
    #   POST https://api.apify.com/v2/acts/{actor_id}/runs?token={APIFY_TOKEN}
    #   Actor recomendado: apify/linkedin-jobs-scraper
    #   Filtrar resultados por fecha >= now() - since_days
    raise NotImplementedError("apify real mode: completar en fase Scout")
