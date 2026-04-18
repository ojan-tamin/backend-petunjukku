from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.studio_message import StudioMessage
from app.models.studio_session import StudioSession
from app.schemas.studio_message import StudioMessageCreate


def get_session_for_user(
    db: Session,
    current_user_id: UUID,
    session_id: UUID,
) -> StudioSession | None:
    return (
        db.query(StudioSession)
        .filter(
            StudioSession.id == session_id,
            StudioSession.user_id == current_user_id,
        )
        .first()
    )


def get_next_sequence_number(db: Session, session_id: UUID) -> int:
    max_sequence = (
        db.query(func.max(StudioMessage.sequence_number))
        .filter(StudioMessage.session_id == session_id)
        .scalar()
    )

    if max_sequence is None:
        return 1
    return max_sequence + 1


def create_message(
    db: Session,
    session: StudioSession,
    message_in: StudioMessageCreate,
) -> StudioMessage:
    next_sequence = get_next_sequence_number(db, session.id)

    message = StudioMessage(
        session_id=session.id,
        sender_type=message_in.sender_type,
        message_type=message_in.message_type,
        message_text=message_in.message_text,
        sequence_number=next_sequence,
    )

    db.add(message)

    session.last_message_at = datetime.now(timezone.utc)
    db.add(session)

    db.commit()
    db.refresh(message)

    return message


def get_messages_by_session(
    db: Session,
    session: StudioSession,
) -> list[StudioMessage]:
    return (
        db.query(StudioMessage)
        .filter(StudioMessage.session_id == session.id)
        .order_by(StudioMessage.sequence_number.asc())
        .all()
    )
