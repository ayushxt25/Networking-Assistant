"""
SQLAlchemy ORM Models
-----------------------
Three tables:
  - users: registered accounts (hashed passwords only, never plaintext)
  - conversation_history: one row per generated conversation, scoped to a user
  - feedback: one row per like/dislike on a suggestion, scoped to a user

Both conversation_history and feedback have a foreign key to users.id, so
each user only ever sees their own history/feedback -- this is the data
isolation that replaces the old single shared JSON files.
"""

from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from app.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(64), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=_utcnow, nullable=False)

    history_entries = relationship(
        "ConversationHistory", back_populates="user", cascade="all, delete-orphan"
    )
    feedback_entries = relationship(
        "Feedback", back_populates="user", cascade="all, delete-orphan"
    )
    recommendation_impressions = relationship(
        "RecommendationImpression", back_populates="user", cascade="all, delete-orphan"
    )
    contacts = relationship("Contact", back_populates="user", cascade="all, delete-orphan")
    events = relationship("Event", back_populates="user", cascade="all, delete-orphan")
    interactions = relationship(
        "Interaction", back_populates="user", cascade="all, delete-orphan"
    )
    follow_ups = relationship("FollowUp", back_populates="user", cascade="all, delete-orphan")
    profile = relationship(
        "UserProfile", back_populates="user", cascade="all, delete-orphan", uselist=False
    )


class ConversationHistory(Base):
    __tablename__ = "conversation_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    description = Column(Text, nullable=False)
    interests = Column(Text, nullable=False)  # stored as a comma-joined string
    themes = Column(Text, nullable=False)  # stored as a comma-joined string
    suggestions = Column(Text, nullable=False)  # stored as a newline-joined string
    created_at = Column(DateTime, default=_utcnow, nullable=False, index=True)

    user = relationship("User", back_populates="history_entries")


class Feedback(Base):
    __tablename__ = "feedback"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    suggestion = Column(Text, nullable=False)
    action = Column(String(16), nullable=False)  # 'like' or 'dislike'
    category = Column(String(32), nullable=True, index=True)
    target_type = Column(String(32), nullable=True, index=True)
    target_id = Column(String(64), nullable=True, index=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=_utcnow, nullable=False, index=True)

    user = relationship("User", back_populates="feedback_entries")


class RecommendationImpression(Base):
    __tablename__ = "recommendation_impressions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    recommendation_id = Column(String(128), nullable=False, index=True)
    recommendation_type = Column(String(100), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    priority_score = Column(Float, nullable=False)
    related_contact_id = Column(Integer, nullable=True, index=True)
    related_event_id = Column(Integer, nullable=True, index=True)
    related_follow_up_id = Column(Integer, nullable=True, index=True)
    reason = Column(Text, nullable=False)
    created_at = Column(DateTime, default=_utcnow, nullable=False, index=True)

    user = relationship("User", back_populates="recommendation_impressions")


class Contact(Base):
    __tablename__ = "contacts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    company = Column(String(255), nullable=False)
    role = Column(String(255), nullable=False)
    email = Column(String(255), nullable=True)
    linkedin_url = Column(String(500), nullable=True)
    notes = Column(Text, nullable=True)
    tags = Column(Text, nullable=True)
    relationship_strength = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=_utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow, nullable=False)

    user = relationship("User", back_populates="contacts")
    interactions = relationship(
        "Interaction", back_populates="contact", cascade="all, delete-orphan"
    )
    follow_ups = relationship("FollowUp", back_populates="contact", cascade="all, delete-orphan")


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    location = Column(String(255), nullable=True)
    event_date = Column(DateTime, nullable=True)
    goals = Column(Text, nullable=True)
    created_at = Column(DateTime, default=_utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow, nullable=False)

    user = relationship("User", back_populates="events")
    interactions = relationship("Interaction", back_populates="event", cascade="all, delete-orphan")
    follow_ups = relationship("FollowUp", back_populates="event", cascade="all, delete-orphan")


class Interaction(Base):
    __tablename__ = "interactions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    contact_id = Column(Integer, ForeignKey("contacts.id"), nullable=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=True, index=True)
    interaction_type = Column(String(100), nullable=False)
    notes = Column(Text, nullable=False)
    sentiment = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=_utcnow, nullable=False, index=True)

    user = relationship("User", back_populates="interactions")
    contact = relationship("Contact", back_populates="interactions")
    event = relationship("Event", back_populates="interactions")


class FollowUp(Base):
    __tablename__ = "follow_ups"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    contact_id = Column(Integer, ForeignKey("contacts.id"), nullable=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    due_date = Column(DateTime, nullable=True)
    status = Column(String(100), nullable=False, default="pending")
    created_at = Column(DateTime, default=_utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow, nullable=False)

    user = relationship("User", back_populates="follow_ups")
    contact = relationship("Contact", back_populates="follow_ups")
    event = relationship("Event", back_populates="follow_ups")


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True, index=True)
    full_name = Column(String(255), nullable=True)
    headline = Column(String(255), nullable=True)
    goals = Column(Text, nullable=True)
    interests = Column(Text, nullable=True)
    preferred_tone = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=_utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow, nullable=False)

    user = relationship("User", back_populates="profile")
