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
import logging
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.agents.scout.strategies import get_strategy
from app.domains.changes.models import Change, Snapshot
from app.domains.sources.models import CompetitorSource

logger = logging.getLogger(__name__)


def compute_hash(content: str) -> str:
    """SHA256 hex del contenido."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def fetch_source_content(source: CompetitorSource) -> str:
    """
    Obtiene el contenido de una fuente segun su tipo.

    Delega a la estrategia correspondiente via Strategy pattern.
    """
    strategy = get_strategy(source.source_type)
    return strategy.fetch(source)


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

    Delega a la estrategia correspondiente via Strategy pattern.
    Si el tipo es desconocido, retorna "general".
    """
    try:
        strategy = get_strategy(source_type)
    except ValueError:
        return "general"
    return strategy.detect_section(content)


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
