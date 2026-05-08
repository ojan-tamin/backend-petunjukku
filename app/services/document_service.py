from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.ai.document_generators import (
    generate_intrakurikuler_document as generate_intrakurikuler_document_template,
    generate_pjbl_document,
)
from app.ai.summary import build_summary_sections, build_summary_text
from app.models.generated_document import GeneratedDocument
from app.models.studio_session import StudioSession
from app.models.user import User
from app.schemas.summary import SummaryResponse
from app.services.session_service import require_session


def build_session_summary(db: Session, user: User, session_id: UUID) -> SummaryResponse:
    session = require_session(db, user, session_id)
    planning_state = session.planning_state
    if not planning_state:
        raise HTTPException(status_code=404, detail="Planning state not found")

    fields = planning_state.collected_fields or {}
    missing = list(planning_state.missing_fields or [])
    summary = build_summary_text(planning_state.workflow_type, fields, missing)

    return SummaryResponse(
        session_id=session.id,
        summary=summary,
        sections=build_summary_sections(planning_state.workflow_type, fields),
        missing_fields=missing,
        is_ready_for_generation=planning_state.is_ready_for_generation,
    )


def generate_document(db: Session, user: User, session_id: UUID) -> GeneratedDocument:
    session = require_session(db, user, session_id)
    planning_state = session.planning_state
    if not planning_state:
        raise HTTPException(status_code=404, detail="Planning state not found")
    if not planning_state.is_ready_for_generation:
        raise HTTPException(
            status_code=403,
            detail="Summary must be approved before document generation",
        )

    fields = planning_state.collected_fields or {}
    if session.document_type.value == "pjbl":
        generated = generate_pjbl_document(fields)
    else:
        generated = generate_intrakurikuler_document_template(fields)

    document = GeneratedDocument(
        session_id=session.id,
        user_id=user.id,
        document_type=session.document_type,
        title=generated["title"],
        content=generated["content"],
        document_output=generated["document_output"],
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    return document


def list_documents(
    db: Session,
    user: User,
    *,
    limit: int = 50,
    offset: int = 0,
) -> list[GeneratedDocument]:
    limit = max(1, min(limit, 100))
    offset = max(0, offset)
    return (
        db.query(GeneratedDocument)
        .filter(GeneratedDocument.user_id == user.id)
        .order_by(GeneratedDocument.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )


def list_session_documents(
    db: Session,
    user: User,
    session_id: UUID,
    *,
    limit: int = 50,
    offset: int = 0,
) -> list[GeneratedDocument]:
    session = require_session(db, user, session_id)
    limit = max(1, min(limit, 100))
    offset = max(0, offset)
    return (
        db.query(GeneratedDocument)
        .filter(
            GeneratedDocument.session_id == session.id,
            GeneratedDocument.user_id == user.id,
        )
        .order_by(GeneratedDocument.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )


def get_document(db: Session, user: User, document_id: UUID) -> GeneratedDocument:
    document = (
        db.query(GeneratedDocument)
        .filter(
            GeneratedDocument.id == document_id,
            GeneratedDocument.user_id == user.id,
        )
        .first()
    )
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    return document


def ensure_session_owner(db: Session, user: User, session_id: UUID) -> StudioSession:
    return require_session(db, user, session_id)
