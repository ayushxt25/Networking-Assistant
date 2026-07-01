from typing import List, Literal, Optional, Type

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.api_utils import normalize_sort_order, paginate_query, pagination_limit, pagination_offset
from app.database import get_db
from app.db_models import Contact, Event, FollowUp, Interaction, User, UserProfile
from app.dependencies import get_current_user
from app.models import (
    ContactCreate,
    ContactResponse,
    ContactUpdate,
    DeleteResponse,
    EventCreate,
    EventResponse,
    EventUpdate,
    FollowUpCreate,
    FollowUpResponse,
    FollowUpUpdate,
    InteractionCreate,
    InteractionResponse,
    InteractionUpdate,
    UserProfileResponse,
    UserProfileUpdate,
)
from app.services.task_dispatcher import dispatch_user_refreshes

router = APIRouter(tags=["relationship-data"])


def _join_list(values: Optional[List[str]]) -> Optional[str]:
    if values is None:
        return None
    cleaned = [value.strip() for value in values if value and value.strip()]
    return ",".join(cleaned) if cleaned else None


def _split_list(value: Optional[str]) -> Optional[List[str]]:
    if not value:
        return None
    items = [item.strip() for item in value.split(",") if item.strip()]
    return items or None


def _get_owned_or_404(db: Session, model: Type, object_id: int, user_id: int):
    instance = db.query(model).filter(model.id == object_id, model.user_id == user_id).first()
    if instance is None:
        raise HTTPException(status_code=404, detail=f"{model.__name__} not found")
    return instance


def _dispatch_refreshes(db: Session, user_id: int) -> None:
    try:
        dispatch_user_refreshes(user_id, db=db)
    except TypeError:
        dispatch_user_refreshes(user_id)


def _validate_optional_links(
    db: Session, user_id: int, contact_id: Optional[int], event_id: Optional[int]
) -> None:
    if contact_id is not None:
        _get_owned_or_404(db, Contact, contact_id, user_id)
    if event_id is not None:
        _get_owned_or_404(db, Event, event_id, user_id)


def _contact_response(contact: Contact) -> ContactResponse:
    return ContactResponse(
        id=contact.id,
        user_id=contact.user_id,
        name=contact.name,
        company=contact.company,
        role=contact.role,
        email=contact.email,
        linkedin_url=contact.linkedin_url,
        notes=contact.notes,
        tags=_split_list(contact.tags),
        relationship_strength=contact.relationship_strength,
        created_at=contact.created_at,
        updated_at=contact.updated_at,
    )


def _event_response(event: Event) -> EventResponse:
    return EventResponse(
        id=event.id,
        user_id=event.user_id,
        title=event.title,
        description=event.description,
        location=event.location,
        event_date=event.event_date,
        goals=_split_list(event.goals),
        created_at=event.created_at,
        updated_at=event.updated_at,
    )


def _interaction_response(interaction: Interaction) -> InteractionResponse:
    return InteractionResponse(
        id=interaction.id,
        user_id=interaction.user_id,
        contact_id=interaction.contact_id,
        event_id=interaction.event_id,
        interaction_type=interaction.interaction_type,
        notes=interaction.notes,
        sentiment=interaction.sentiment,
        created_at=interaction.created_at,
    )


def _follow_up_response(follow_up: FollowUp) -> FollowUpResponse:
    return FollowUpResponse(
        id=follow_up.id,
        user_id=follow_up.user_id,
        contact_id=follow_up.contact_id,
        event_id=follow_up.event_id,
        title=follow_up.title,
        description=follow_up.description,
        due_date=follow_up.due_date,
        status=follow_up.status,
        created_at=follow_up.created_at,
        updated_at=follow_up.updated_at,
    )


def _profile_response(profile: UserProfile) -> UserProfileResponse:
    return UserProfileResponse(
        id=profile.id,
        user_id=profile.user_id,
        full_name=profile.full_name,
        headline=profile.headline,
        goals=_split_list(profile.goals),
        interests=_split_list(profile.interests),
        preferred_tone=profile.preferred_tone,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    )


@router.post("/contacts", response_model=ContactResponse, status_code=status.HTTP_201_CREATED)
def create_contact(
    request: Request,
    body: ContactCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ContactResponse:
    contact = Contact(user_id=current_user.id, **body.model_dump(exclude={"tags"}), tags=_join_list(body.tags))
    db.add(contact)
    db.commit()
    db.refresh(contact)
    _dispatch_refreshes(db, current_user.id)
    return _contact_response(contact)


@router.get("/contacts", response_model=List[ContactResponse])
def list_contacts(
    request: Request,
    limit: int = pagination_limit(),
    offset: int = pagination_offset(),
    q: Optional[str] = None,
    company: Optional[str] = None,
    tag: Optional[str] = None,
    sort_by: Literal["created_at", "updated_at", "name", "company", "relationship_strength"] = "created_at",
    sort_order: Literal["asc", "desc"] = "desc",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[ContactResponse]:
    query = db.query(Contact).filter(Contact.user_id == current_user.id)
    if q:
        pattern = f"%{q}%"
        query = query.filter(
            or_(
                Contact.name.ilike(pattern),
                Contact.company.ilike(pattern),
                Contact.role.ilike(pattern),
                Contact.notes.ilike(pattern),
            )
        )
    if company:
        query = query.filter(Contact.company.ilike(f"%{company}%"))
    if tag:
        query = query.filter(Contact.tags.ilike(f"%{tag}%"))
    sort_column = getattr(Contact, sort_by)
    query = query.order_by(sort_column.desc() if normalize_sort_order(sort_order) else sort_column.asc(), Contact.id.desc())
    contacts = paginate_query(query, limit, offset).all()
    return [_contact_response(contact) for contact in contacts]


@router.get("/contacts/{contact_id}", response_model=ContactResponse)
def get_contact(
    request: Request,
    contact_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ContactResponse:
    return _contact_response(_get_owned_or_404(db, Contact, contact_id, current_user.id))


@router.put("/contacts/{contact_id}", response_model=ContactResponse)
def update_contact(
    request: Request,
    contact_id: int,
    body: ContactUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ContactResponse:
    contact = _get_owned_or_404(db, Contact, contact_id, current_user.id)
    updates = body.model_dump(exclude_unset=True)
    if "tags" in updates:
        contact.tags = _join_list(updates.pop("tags"))
    for field, value in updates.items():
        setattr(contact, field, value)
    db.commit()
    db.refresh(contact)
    _dispatch_refreshes(db, current_user.id)
    return _contact_response(contact)


@router.delete("/contacts/{contact_id}", response_model=DeleteResponse)
def delete_contact(
    request: Request,
    contact_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DeleteResponse:
    contact = _get_owned_or_404(db, Contact, contact_id, current_user.id)
    db.delete(contact)
    db.commit()
    _dispatch_refreshes(db, current_user.id)
    return DeleteResponse()


@router.post("/events", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
def create_event(
    request: Request,
    body: EventCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> EventResponse:
    event = Event(user_id=current_user.id, **body.model_dump(exclude={"goals"}), goals=_join_list(body.goals))
    db.add(event)
    db.commit()
    db.refresh(event)
    _dispatch_refreshes(db, current_user.id)
    return _event_response(event)


@router.get("/events", response_model=List[EventResponse])
def list_events(
    request: Request,
    limit: int = pagination_limit(),
    offset: int = pagination_offset(),
    q: Optional[str] = None,
    location: Optional[str] = None,
    sort_by: Literal["created_at", "updated_at", "event_date", "title"] = "created_at",
    sort_order: Literal["asc", "desc"] = "desc",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[EventResponse]:
    query = db.query(Event).filter(Event.user_id == current_user.id)
    if q:
        pattern = f"%{q}%"
        query = query.filter(or_(Event.title.ilike(pattern), Event.description.ilike(pattern)))
    if location:
        query = query.filter(Event.location.ilike(f"%{location}%"))
    sort_column = getattr(Event, sort_by)
    query = query.order_by(sort_column.desc() if normalize_sort_order(sort_order) else sort_column.asc(), Event.id.desc())
    events = paginate_query(query, limit, offset).all()
    return [_event_response(event) for event in events]


@router.get("/events/{event_id}", response_model=EventResponse)
def get_event(
    request: Request,
    event_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> EventResponse:
    return _event_response(_get_owned_or_404(db, Event, event_id, current_user.id))


@router.put("/events/{event_id}", response_model=EventResponse)
def update_event(
    request: Request,
    event_id: int,
    body: EventUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> EventResponse:
    event = _get_owned_or_404(db, Event, event_id, current_user.id)
    updates = body.model_dump(exclude_unset=True)
    if "goals" in updates:
        event.goals = _join_list(updates.pop("goals"))
    for field, value in updates.items():
        setattr(event, field, value)
    db.commit()
    db.refresh(event)
    _dispatch_refreshes(db, current_user.id)
    return _event_response(event)


@router.delete("/events/{event_id}", response_model=DeleteResponse)
def delete_event(
    request: Request,
    event_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DeleteResponse:
    event = _get_owned_or_404(db, Event, event_id, current_user.id)
    db.delete(event)
    db.commit()
    _dispatch_refreshes(db, current_user.id)
    return DeleteResponse()


@router.post("/interactions", response_model=InteractionResponse, status_code=status.HTTP_201_CREATED)
def create_interaction(
    request: Request,
    body: InteractionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> InteractionResponse:
    _validate_optional_links(db, current_user.id, body.contact_id, body.event_id)
    interaction = Interaction(user_id=current_user.id, **body.model_dump())
    db.add(interaction)
    db.commit()
    db.refresh(interaction)
    _dispatch_refreshes(db, current_user.id)
    return _interaction_response(interaction)


@router.get("/interactions", response_model=List[InteractionResponse])
def list_interactions(
    request: Request,
    limit: int = pagination_limit(),
    offset: int = pagination_offset(),
    interaction_type: Optional[str] = None,
    contact_id: Optional[int] = None,
    event_id: Optional[int] = None,
    sort_order: Literal["asc", "desc"] = "desc",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[InteractionResponse]:
    query = db.query(Interaction).filter(Interaction.user_id == current_user.id)
    if interaction_type:
        query = query.filter(Interaction.interaction_type.ilike(f"%{interaction_type}%"))
    if contact_id is not None:
        query = query.filter(Interaction.contact_id == contact_id)
    if event_id is not None:
        query = query.filter(Interaction.event_id == event_id)
    query = query.order_by(
        Interaction.created_at.desc() if normalize_sort_order(sort_order) else Interaction.created_at.asc(),
        Interaction.id.desc(),
    )
    interactions = paginate_query(query, limit, offset).all()
    return [_interaction_response(interaction) for interaction in interactions]


@router.get("/interactions/{interaction_id}", response_model=InteractionResponse)
def get_interaction(
    request: Request,
    interaction_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> InteractionResponse:
    return _interaction_response(_get_owned_or_404(db, Interaction, interaction_id, current_user.id))


@router.put("/interactions/{interaction_id}", response_model=InteractionResponse)
def update_interaction(
    request: Request,
    interaction_id: int,
    body: InteractionUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> InteractionResponse:
    interaction = _get_owned_or_404(db, Interaction, interaction_id, current_user.id)
    updates = body.model_dump(exclude_unset=True)
    contact_id = updates.get("contact_id", interaction.contact_id)
    event_id = updates.get("event_id", interaction.event_id)
    _validate_optional_links(db, current_user.id, contact_id, event_id)
    for field, value in updates.items():
        setattr(interaction, field, value)
    db.commit()
    db.refresh(interaction)
    _dispatch_refreshes(db, current_user.id)
    return _interaction_response(interaction)


@router.delete("/interactions/{interaction_id}", response_model=DeleteResponse)
def delete_interaction(
    request: Request,
    interaction_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DeleteResponse:
    interaction = _get_owned_or_404(db, Interaction, interaction_id, current_user.id)
    db.delete(interaction)
    db.commit()
    _dispatch_refreshes(db, current_user.id)
    return DeleteResponse()


@router.post("/follow-ups", response_model=FollowUpResponse, status_code=status.HTTP_201_CREATED)
def create_follow_up(
    request: Request,
    body: FollowUpCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FollowUpResponse:
    _validate_optional_links(db, current_user.id, body.contact_id, body.event_id)
    follow_up = FollowUp(user_id=current_user.id, **body.model_dump())
    db.add(follow_up)
    db.commit()
    db.refresh(follow_up)
    _dispatch_refreshes(db, current_user.id)
    return _follow_up_response(follow_up)


@router.get("/follow-ups", response_model=List[FollowUpResponse])
def list_follow_ups(
    request: Request,
    limit: int = pagination_limit(),
    offset: int = pagination_offset(),
    status_filter: Optional[str] = Query(default=None, alias="status"),
    contact_id: Optional[int] = None,
    event_id: Optional[int] = None,
    sort_by: Literal["created_at", "updated_at", "due_date", "title"] = "created_at",
    sort_order: Literal["asc", "desc"] = "desc",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[FollowUpResponse]:
    query = db.query(FollowUp).filter(FollowUp.user_id == current_user.id)
    if status_filter:
        query = query.filter(FollowUp.status.ilike(f"%{status_filter}%"))
    if contact_id is not None:
        query = query.filter(FollowUp.contact_id == contact_id)
    if event_id is not None:
        query = query.filter(FollowUp.event_id == event_id)
    sort_column = getattr(FollowUp, sort_by)
    query = query.order_by(sort_column.desc() if normalize_sort_order(sort_order) else sort_column.asc(), FollowUp.id.desc())
    follow_ups = paginate_query(query, limit, offset).all()
    return [_follow_up_response(follow_up) for follow_up in follow_ups]


@router.get("/follow-ups/{follow_up_id}", response_model=FollowUpResponse)
def get_follow_up(
    request: Request,
    follow_up_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FollowUpResponse:
    return _follow_up_response(_get_owned_or_404(db, FollowUp, follow_up_id, current_user.id))


@router.put("/follow-ups/{follow_up_id}", response_model=FollowUpResponse)
def update_follow_up(
    request: Request,
    follow_up_id: int,
    body: FollowUpUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FollowUpResponse:
    follow_up = _get_owned_or_404(db, FollowUp, follow_up_id, current_user.id)
    updates = body.model_dump(exclude_unset=True)
    contact_id = updates.get("contact_id", follow_up.contact_id)
    event_id = updates.get("event_id", follow_up.event_id)
    _validate_optional_links(db, current_user.id, contact_id, event_id)
    for field, value in updates.items():
        setattr(follow_up, field, value)
    db.commit()
    db.refresh(follow_up)
    _dispatch_refreshes(db, current_user.id)
    return _follow_up_response(follow_up)


@router.delete("/follow-ups/{follow_up_id}", response_model=DeleteResponse)
def delete_follow_up(
    request: Request,
    follow_up_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DeleteResponse:
    follow_up = _get_owned_or_404(db, FollowUp, follow_up_id, current_user.id)
    db.delete(follow_up)
    db.commit()
    _dispatch_refreshes(db, current_user.id)
    return DeleteResponse()


@router.get("/profile", response_model=UserProfileResponse)
def get_profile(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserProfileResponse:
    profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()
    if profile is None:
        raise HTTPException(status_code=404, detail="UserProfile not found")
    return _profile_response(profile)


@router.put("/profile", response_model=UserProfileResponse)
def upsert_profile(
    request: Request,
    body: UserProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserProfileResponse:
    profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()
    if profile is None:
        profile = UserProfile(user_id=current_user.id)
        db.add(profile)

    updates = body.model_dump(exclude_unset=True)
    if "goals" in updates:
        profile.goals = _join_list(updates.pop("goals"))
    if "interests" in updates:
        profile.interests = _join_list(updates.pop("interests"))
    for field, value in updates.items():
        setattr(profile, field, value)
    db.commit()
    db.refresh(profile)
    _dispatch_refreshes(db, current_user.id)
    return _profile_response(profile)


@router.delete("/profile", response_model=DeleteResponse)
def delete_profile(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DeleteResponse:
    profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()
    if profile is None:
        raise HTTPException(status_code=404, detail="UserProfile not found")
    db.delete(profile)
    db.commit()
    _dispatch_refreshes(db, current_user.id)
    return DeleteResponse()
