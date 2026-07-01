from dataclasses import dataclass
from typing import List, Optional, Sequence

from sqlalchemy.orm import Session

from app.db_models import Contact, Event, FollowUp, Interaction, UserProfile
from app.services.semantic_memory_service import semantic_search_memories


def _split_csv(value: Optional[str]) -> List[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def _build_keywords(description: str, interests: Sequence[str], themes: Sequence[str]) -> set[str]:
    raw_parts = [description, *interests, *themes]
    keywords = set()
    for part in raw_parts:
        for token in part.lower().replace(",", " ").split():
            cleaned = token.strip(" .!?;:-()[]{}\"'")
            if len(cleaned) >= 3:
                keywords.add(cleaned)
    return keywords


def _match_score(text: str, keywords: set[str]) -> int:
    lower_text = text.lower()
    return sum(1 for keyword in keywords if keyword in lower_text)


@dataclass
class GenerationContext:
    profile_summary: Optional[str]
    contacts_summary: List[str]
    interactions_summary: List[str]
    events_summary: List[str]
    follow_ups_summary: List[str]
    semantic_memory_summary: List[str]

    @property
    def combined_summary(self) -> Optional[str]:
        sections = []

        if self.profile_summary:
            sections.append(f"User profile: {self.profile_summary}")
        if self.contacts_summary:
            sections.append("Contacts: " + " | ".join(self.contacts_summary))
        if self.interactions_summary:
            sections.append("Interactions: " + " | ".join(self.interactions_summary))
        if self.events_summary:
            sections.append("Events: " + " | ".join(self.events_summary))
        if self.follow_ups_summary:
            sections.append("Follow-ups: " + " | ".join(self.follow_ups_summary))
        if self.semantic_memory_summary:
            sections.append("Semantic memory: " + " | ".join(self.semantic_memory_summary))

        return "\n".join(sections) if sections else None


def _select_relevant_contacts(db: Session, user_id: int, keywords: set[str]) -> List[Contact]:
    contacts = db.query(Contact).filter(Contact.user_id == user_id).order_by(Contact.updated_at.desc()).all()
    ranked = sorted(
        contacts,
        key=lambda contact: (
            -_match_score(
                " ".join(
                    filter(
                        None,
                        [
                            contact.name,
                            contact.company,
                            contact.role,
                            contact.notes,
                            contact.tags,
                        ],
                    )
                ),
                keywords,
            ),
            contact.id,
        ),
    )
    return ranked[:3]


def _select_relevant_events(db: Session, user_id: int, keywords: set[str]) -> List[Event]:
    events = db.query(Event).filter(Event.user_id == user_id).order_by(Event.updated_at.desc()).all()
    ranked = sorted(
        events,
        key=lambda event: (
            -_match_score(
                " ".join(filter(None, [event.title, event.description, event.location, event.goals])),
                keywords,
            ),
            event.id,
        ),
    )
    return ranked[:3]


def assemble_generation_context(
    db: Session,
    user_id: int,
    description: str,
    interests: Sequence[str],
    themes: Sequence[str],
) -> GenerationContext:
    keywords = _build_keywords(description, interests, themes)

    profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
    contacts = _select_relevant_contacts(db, user_id, keywords)
    events = _select_relevant_events(db, user_id, keywords)
    interactions = (
        db.query(Interaction)
        .filter(Interaction.user_id == user_id)
        .order_by(Interaction.created_at.desc())
        .limit(5)
        .all()
    )
    follow_ups = (
        db.query(FollowUp)
        .filter(FollowUp.user_id == user_id)
        .order_by(FollowUp.updated_at.desc())
        .limit(5)
        .all()
    )

    profile_summary = None
    if profile is not None:
        summary_parts = []
        if profile.full_name:
            summary_parts.append(f"name={profile.full_name}")
        if profile.headline:
            summary_parts.append(f"headline={profile.headline}")
        if profile.goals:
            summary_parts.append(f"goals={'; '.join(_split_csv(profile.goals))}")
        if profile.interests:
            summary_parts.append(f"interests={'; '.join(_split_csv(profile.interests))}")
        if profile.preferred_tone:
            summary_parts.append(f"preferred tone={profile.preferred_tone}")
        profile_summary = ", ".join(summary_parts) if summary_parts else None

    contacts_summary = [
        " / ".join(
            filter(
                None,
                [
                    contact.name,
                    contact.role,
                    contact.company,
                    contact.notes,
                ],
            )
        )
        for contact in contacts
    ]

    interactions_summary = []
    for interaction in interactions:
        score = _match_score(
            " ".join(filter(None, [interaction.interaction_type, interaction.notes, interaction.sentiment])),
            keywords,
        )
        if score > 0 or not keywords:
            interactions_summary.append(
                " / ".join(
                    filter(
                        None,
                        [
                            interaction.interaction_type,
                            interaction.notes,
                            interaction.sentiment,
                        ],
                    )
                )
            )
    interactions_summary = interactions_summary[:3]

    events_summary = [
        " / ".join(
            filter(
                None,
                [
                    event.title,
                    event.location,
                    event.description,
                ],
            )
        )
        for event in events
    ]

    follow_ups_summary = []
    for follow_up in follow_ups:
        score = _match_score(
            " ".join(filter(None, [follow_up.title, follow_up.description, follow_up.status])),
            keywords,
        )
        if score > 0 or not keywords:
            follow_ups_summary.append(
                " / ".join(
                    filter(
                        None,
                        [
                            follow_up.title,
                            follow_up.description,
                            follow_up.status,
                        ],
                    )
                )
            )
    follow_ups_summary = follow_ups_summary[:3]

    semantic_matches = semantic_search_memories(
        db=db,
        query_text=" ".join([description, *interests, *themes]),
        user_id=user_id,
        top_k=3,
    )
    semantic_memory_summary = [match.text for match in semantic_matches]

    return GenerationContext(
        profile_summary=profile_summary,
        contacts_summary=contacts_summary,
        interactions_summary=interactions_summary,
        events_summary=events_summary,
        follow_ups_summary=follow_ups_summary,
        semantic_memory_summary=semantic_memory_summary,
    )
