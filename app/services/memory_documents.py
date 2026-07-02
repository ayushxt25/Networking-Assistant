from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.db_models import Contact, Event, FollowUp, Interaction, UserProfile


def _split_csv(value: Optional[str]) -> List[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def _isoformat_timestamp(value) -> Optional[str]:
    if value is None:
        return None
    return value.isoformat()


@dataclass
class MemoryDocument:
    id: str
    user_id: int
    entity_type: str
    record_id: int
    text: str
    metadata: Dict[str, Any]


def build_memory_documents(db: Session, user_id: int) -> List[MemoryDocument]:
    documents: List[MemoryDocument] = []

    contacts = db.query(Contact).filter(Contact.user_id == user_id).all()
    for contact in contacts:
        text = " | ".join(
            filter(
                None,
                [
                    f"Contact {contact.name}",
                    contact.role,
                    contact.company,
                    contact.email,
                    contact.linkedin_url,
                    contact.notes,
                    ", ".join(_split_csv(contact.tags)),
                ],
            )
        )
        documents.append(
            MemoryDocument(
                id=f"contact:{contact.id}",
                user_id=user_id,
                entity_type="contact",
                record_id=contact.id,
                text=text,
                metadata={
                    "user_id": user_id,
                    "entity_type": "contact",
                    "record_id": contact.id,
                    "name": contact.name,
                    "company": contact.company,
                    "role": contact.role,
                    "tags": ", ".join(_split_csv(contact.tags)),
                    "relationship_strength": contact.relationship_strength,
                    "created_at": _isoformat_timestamp(contact.created_at),
                    "updated_at": _isoformat_timestamp(contact.updated_at),
                },
            )
        )

    events = db.query(Event).filter(Event.user_id == user_id).all()
    for event in events:
        text = " | ".join(
            filter(
                None,
                [
                    f"Event {event.title}",
                    event.location,
                    event.description,
                    ", ".join(_split_csv(event.goals)),
                ],
            )
        )
        documents.append(
            MemoryDocument(
                id=f"event:{event.id}",
                user_id=user_id,
                entity_type="event",
                record_id=event.id,
                text=text,
                metadata={
                    "user_id": user_id,
                    "entity_type": "event",
                    "record_id": event.id,
                    "title": event.title,
                    "location": event.location,
                    "goals": ", ".join(_split_csv(event.goals)),
                    "event_date": _isoformat_timestamp(event.event_date),
                    "created_at": _isoformat_timestamp(event.created_at),
                    "updated_at": _isoformat_timestamp(event.updated_at),
                },
            )
        )

    interactions = db.query(Interaction).filter(Interaction.user_id == user_id).all()
    for interaction in interactions:
        text = " | ".join(
            filter(
                None,
                [
                    f"Interaction {interaction.interaction_type}",
                    interaction.notes,
                    interaction.sentiment,
                ],
            )
        )
        documents.append(
            MemoryDocument(
                id=f"interaction:{interaction.id}",
                user_id=user_id,
                entity_type="interaction",
                record_id=interaction.id,
                text=text,
                metadata={
                    "user_id": user_id,
                    "entity_type": "interaction",
                    "record_id": interaction.id,
                    "contact_id": interaction.contact_id,
                    "event_id": interaction.event_id,
                    "interaction_type": interaction.interaction_type,
                    "sentiment": interaction.sentiment,
                    "created_at": _isoformat_timestamp(interaction.created_at),
                },
            )
        )

    follow_ups = db.query(FollowUp).filter(FollowUp.user_id == user_id).all()
    for follow_up in follow_ups:
        text = " | ".join(
            filter(
                None,
                [
                    f"Follow-up {follow_up.title}",
                    follow_up.description,
                    follow_up.status,
                ],
            )
        )
        documents.append(
            MemoryDocument(
                id=f"follow_up:{follow_up.id}",
                user_id=user_id,
                entity_type="follow_up",
                record_id=follow_up.id,
                text=text,
                metadata={
                    "user_id": user_id,
                    "entity_type": "follow_up",
                    "record_id": follow_up.id,
                    "contact_id": follow_up.contact_id,
                    "event_id": follow_up.event_id,
                    "status": follow_up.status,
                    "due_date": _isoformat_timestamp(follow_up.due_date),
                    "created_at": _isoformat_timestamp(follow_up.created_at),
                    "updated_at": _isoformat_timestamp(follow_up.updated_at),
                },
            )
        )

    profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
    if profile is not None:
        text = " | ".join(
            filter(
                None,
                [
                    f"Profile {profile.full_name}" if profile.full_name else "Profile",
                    profile.headline,
                    ", ".join(_split_csv(profile.goals)),
                    ", ".join(_split_csv(profile.interests)),
                    profile.preferred_tone,
                ],
            )
        )
        documents.append(
            MemoryDocument(
                id=f"profile:{profile.id}",
                user_id=user_id,
                entity_type="profile",
                record_id=profile.id,
                text=text,
                metadata={
                    "user_id": user_id,
                    "entity_type": "profile",
                    "record_id": profile.id,
                    "goals": ", ".join(_split_csv(profile.goals)),
                    "interests": ", ".join(_split_csv(profile.interests)),
                    "preferred_tone": profile.preferred_tone,
                    "created_at": _isoformat_timestamp(profile.created_at),
                    "updated_at": _isoformat_timestamp(profile.updated_at),
                },
            )
        )

    return documents
