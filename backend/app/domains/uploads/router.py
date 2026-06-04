"""Router de uploads de PDF."""

import logging
import uuid

from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_db_user
from app.domains.auth.models import User
from app.domains.competitors.models import Competitor
from app.integrations import storage
from app.workers.tasks import parse_pdf

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/uploads", tags=["uploads"])


@router.post("/pdf", status_code=202)
def upload_pdf(
    file: UploadFile,
    competitor_id: uuid.UUID = Form(...),
    user: User = Depends(get_current_db_user),
    db: Session = Depends(get_db),
) -> dict:
    """
    Sube un PDF a R2 y encola la tarea parse_pdf.
    Valida que el competidor pertenezca al usuario autenticado.
    """
    if user.company is None:
        raise HTTPException(status_code=400, detail="El usuario no tiene empresa configurada.")

    competitor = (
        db.query(Competitor)
        .filter(
            Competitor.id == competitor_id,
            Competitor.company_id == user.company.id,
            Competitor.is_active.is_(True),
        )
        .first()
    )
    if competitor is None:
        raise HTTPException(status_code=404, detail="Competidor no encontrado")

    content = file.file.read()
    key = f"pdfs/{competitor_id}/{uuid.uuid4()}.pdf"
    storage.upload_bytes(key, content, "application/pdf")
    parse_pdf.delay(key, str(competitor_id))

    logger.info("uploads: pdf encolado key=%s competitor=%s", key, competitor_id)
    return {"key": key, "status": "encolado", "competitor_id": str(competitor_id)}
