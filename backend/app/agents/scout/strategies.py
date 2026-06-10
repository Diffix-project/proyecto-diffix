"""
Estrategias para el agente Scout.

Cada estrategia encapsula la lógica de fetch y detección de sección
para un tipo de fuente específico (website, mercadolibre, jobs, pdf).
"""

from abc import ABC, abstractmethod

from app.domains.sources.models import CompetitorSource
from app.integrations.apify import get_job_postings
from app.integrations.mercadolibre import get_seller_state
from app.integrations.scraper import fetch_clean_text


def normalize_to_text(data) -> str:
    """Serializa dicts/lists a texto deterministico (sorted keys, indent fijo)."""
    import json

    return json.dumps(data, sort_keys=True, ensure_ascii=False, indent=2)


class SourceStrategy(ABC):
    """Interfaz base para estrategias de fuentes."""

    @abstractmethod
    def fetch(self, source: CompetitorSource) -> str:
        """Obtiene el contenido de la fuente."""
        pass

    @abstractmethod
    def detect_section(self, content: str) -> str:
        """Determina la sección del cambio."""
        pass


class WebsiteStrategy(SourceStrategy):
    """Estrategia para sitios web (scraping con Playwright)."""

    def fetch(self, source: CompetitorSource) -> str:
        if not source.source_url:
            raise ValueError(f"Fuente website sin source_url (source_id={source.id})")
        return fetch_clean_text(source.source_url)

    def detect_section(self, content: str) -> str:
        content_lower = content.lower()
        if any(word in content_lower for word in ["precio", "price", "$", "tarifa"]):
            return "pricing"
        if any(word in content_lower for word in ["producto", "catalogo", "item"]):
            return "features"
        return "general"


class MercadoLibreStrategy(SourceStrategy):
    """Estrategia para MercadoLibre (API oficial)."""

    def fetch(self, source: CompetitorSource) -> str:
        config = source.config or {}
        seller_id = config.get("seller_id") or source.source_url
        if not seller_id:
            raise ValueError(f"Fuente mercadolibre sin seller_id en config (source_id={source.id})")
        data = get_seller_state(seller_id)
        return normalize_to_text(data)

    def detect_section(self, content: str) -> str:
        return "pricing"


class JobsStrategy(SourceStrategy):
    """Estrategia para ofertas de trabajo (Apify)."""

    def fetch(self, source: CompetitorSource) -> str:
        competitor = source.competitor
        if not competitor:
            raise ValueError(f"Fuente jobs sin competidor asociado (source_id={source.id})")
        config = source.config or {}
        since_days = config.get("since_days", 30)
        postings = get_job_postings(competitor.name, since_days=since_days)
        return normalize_to_text(postings)

    def detect_section(self, content: str) -> str:
        return "jobs"


class PdfStrategy(SourceStrategy):
    """Estrategia para PDFs (pendiente de implementar)."""

    def fetch(self, source: CompetitorSource) -> str:
        raise NotImplementedError("Fuente pdf: pendiente de implementar")

    def detect_section(self, content: str) -> str:
        return "pdf"


STRATEGIES: dict[str, SourceStrategy] = {
    "website": WebsiteStrategy(),
    "mercadolibre": MercadoLibreStrategy(),
    "jobs": JobsStrategy(),
    "pdf": PdfStrategy(),
}


def get_strategy(source_type: str) -> SourceStrategy:
    """Obtiene la estrategia para un tipo de fuente."""
    if source_type not in STRATEGIES:
        raise ValueError(f"source_type desconocido: {source_type!r}")
    return STRATEGIES[source_type]
