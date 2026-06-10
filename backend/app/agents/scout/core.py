"""
Logica central del agente Scout.

Funciones publicas:
  fetch_source_content(source) -> str
  compute_hash(content) -> str
  get_last_snapshot(db, source_id) -> Snapshot | None
  create_snapshot(db, source, content, content_hash) -> Snapshot
  compute_diff(before_content, after_content) -> tuple[str, dict]
  detect_section(source_type, content) -> str
  create_change(db, source, snapshot_before, snapshot_after, diff_text, diff_raw, section) -> Change

El dispatch se hace por source_type. La normalizacion garantiza hashes
deterministicos entre corridas con los mismos datos.
"""

import difflib
import hashlib
import json
import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.domains.changes.models import Change, Snapshot
from app.domains.sources.models import CompetitorSource
from app.integrations.apify import get_job_postings
from app.integrations.mercadolibre import get_seller_state
from app.integrations.scraper import fetch_clean_text

logger = logging.getLogger(__name__)


def normalize_to_text(data: Any) -> str:
    """Serializa dicts/lists a texto deterministico (sorted keys, indent fijo)."""
    return json.dumps(data, sort_keys=True, ensure_ascii=False, indent=2)


def compute_hash(content: str) -> str:
    """SHA256 hex del contenido."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def fetch_source_content(source: CompetitorSource) -> str:
    """
    Obtiene el contenido de una fuente segun su tipo.

    - website: scraping con Playwright (mock en dev)
    - mercadolibre: API oficial de ML (mock en dev)
    - jobs: Apify para LinkedIn Jobs (mock en dev)
    - pdf: no implementado en este milestone
    """
    source_type = source.source_type
    config = source.config or {}

    if source_type == "website":
        if not source.source_url:
            raise ValueError(f"Fuente website sin source_url (source_id={source.id})")
        return fetch_clean_text(source.source_url)

    if source_type == "mercadolibre":
        seller_id = config.get("seller_id") or source.source_url
        if not seller_id:
            raise ValueError(
                f"Fuente mercadolibre sin seller_id en config (source_id={source.id})"
            )
        data = get_seller_state(seller_id)
        return normalize_to_text(data)

    if source_type == "jobs":
        competitor = source.competitor
        if not competitor:
            raise ValueError(f"Fuente jobs sin competidor asociado (source_id={source.id})")
        since_days = config.get("since_days", 30)
        postings = get_job_postings(competitor.name, since_days=since_days)
        return normalize_to_text(postings)

    if source_type == "pdf":
        raise NotImplementedError("Fuente pdf: pendiente de implementar")

    raise ValueError(f"source_type desconocido: {source_type!r} (source_id={source.id})")


def get_last_snapshot(db: Session, source_id) -> Snapshot | None:
    """Consulta el ultimo snapshot de una fuente, ordenado por captured_at DESC."""
    return (
        db.query(Snapshot)
        .filter(Snapshot.source_id == source_id)
        .order_by(Snapshot.captured_at.desc())
        .first()
    )


def create_snapshot(
    db: Session,
    source: CompetitorSource,
    content: str,
    content_hash: str,
) -> Snapshot:
    """Crea un Snapshot con el contenido y hash proporcionados."""
    snapshot = Snapshot(
        competitor_id=source.competitor_id,
        source_id=source.id,
        source_type=source.source_type,
        content_hash=content_hash,
        content=content,
        raw_url=source.source_url,
        captured_at=datetime.now(UTC),
    )
    db.add(snapshot)
    db.flush()
    return snapshot


def compute_diff(before_content: str, after_content: str) -> tuple[str, dict]:
    """
    Genera diff_text (legible) y diff_raw (JSONB estructurado).

    diff_text: formato unified diff en espanol.
    diff_raw: dict con 'added', 'removed', 'changed' (lineas).
    """
    before_lines = before_content.splitlines(keepends=True)
    after_lines = after_content.splitlines(keepends=True)

    diff = list(
        difflib.unified_diff(
            before_lines,
            after_lines,
            fromfile="antes",
            tofile="despues",
            lineterm="",
        )
    )
    diff_text = "".join(diff)

    added = []
    removed = []
    for line in diff:
        if line.startswith("+") and not line.startswith("+++"):
            added.append(line[1:].rstrip())
        elif line.startswith("-") and not line.startswith("---"):
            removed.append(line[1:].rstrip())

    diff_raw = {
        "added": added,
        "removed": removed,
    }

    return diff_text, diff_raw


def detect_section(source_type: str, content: str) -> str:
    """
    Determina la seccion del cambio basada en source_type y contenido.

    - jobs -> "jobs"
    - mercadolibre -> "pricing"
    - pdf -> "pdf"
    - website -> heuristica por keywords o "general"
    """
    if source_type == "jobs":
        return "jobs"
    if source_type == "mercadolibre":
        return "pricing"
    if source_type == "pdf":
        return "pdf"

    if source_type == "website":
        content_lower = content.lower()
        if any(word in content_lower for word in ["precio", "price", "$", "tarifa"]):
            return "pricing"
        if any(word in content_lower for word in ["producto", "catalogo", "item"]):
            return "features"
        return "general"

    return "general"


def create_change(
    db: Session,
    source: CompetitorSource,
    snapshot_before: Snapshot | None,
    snapshot_after: Snapshot,
    diff_text: str,
    diff_raw: dict,
    section: str,
) -> Change:
    """Crea un Change vinculado a los snapshots y con status='pending'."""
    change = Change(
        competitor_id=source.competitor_id,
        source_id=source.id,
        source_type=source.source_type,
        section=section,
        diff_text=diff_text,
        diff_raw=diff_raw,
        snapshot_before_id=snapshot_before.id if snapshot_before else None,
        snapshot_after_id=snapshot_after.id,
        status="pending",
    )
    db.add(change)
    db.flush()
    return change
