"""
Pydantic models that define the data contracts between the frontend and
backend. Using BaseModel gives us automatic request validation (FastAPI
returns a 422 with a clear error message if a field is missing or has the
wrong type) and automatic documentation in the Swagger UI.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class EventAnalysisRequest(BaseModel):
    """Input for the /analyze-event endpoint."""
    description: str = Field(..., description="Description of the networking event")
    candidate_labels: Optional[List[str]] = Field(
        default=None,
        description="Optional custom list of themes to classify against. "
                     "If omitted, a default set of networking-relevant themes is used.",
    )


class EventAnalysisResponse(BaseModel):
    themes: List[str]


class FactCheckRequest(BaseModel):
    """Input for the /fact-check endpoint."""
    query: str = Field(..., description="Topic or phrase to fact-check via Wikipedia")


class FactCheckResponse(BaseModel):
    query: str
    summary: str


class ConversationRequest(BaseModel):
    """Input for the /generate-conversation endpoint."""
    description: str = Field(..., description="Description of the networking event")
    interests: List[str] = Field(..., description="List of the user's interests")


class ConversationResponse(BaseModel):
    themes: List[str]
    suggestions: List[str]


class FeedbackRequest(BaseModel):
    """Input for the /feedback endpoint."""
    suggestion: str = Field(..., description="The exact suggestion text being rated")
    action: Optional[str] = Field(default=None, description="Legacy value: either 'like' or 'dislike'")
    category: Optional[str] = Field(default=None, description="Structured feedback category")
    target_type: Optional[str] = Field(default=None, description="generation_suggestion, recommendation, contact, or interaction")
    target_id: Optional[str] = Field(default=None, description="Entity identifier for the feedback target")
    notes: Optional[str] = Field(default=None, description="Optional free-text feedback note")


# ---------------------------------------------------------------------------
# Auth schemas
# ---------------------------------------------------------------------------

class UserRegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=64)
    password: str = Field(..., min_length=8, max_length=128)


class UserLoginRequest(BaseModel):
    username: str
    password: str


class UserResponse(BaseModel):
    id: int
    username: str

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ---------------------------------------------------------------------------
# History schemas
# ---------------------------------------------------------------------------

class HistoryEntryResponse(BaseModel):
    id: int
    description: str
    interests: List[str]
    themes: List[str]
    suggestions: List[str]
    created_at: str


class DeleteResponse(BaseModel):
    status: str = "ok"


class ContactBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    company: str = Field(..., min_length=1, max_length=255)
    role: str = Field(..., min_length=1, max_length=255)
    email: Optional[str] = None
    linkedin_url: Optional[str] = Field(default=None, max_length=500)
    notes: Optional[str] = None
    tags: Optional[List[str]] = None
    relationship_strength: Optional[int] = Field(default=None, ge=1, le=5)


class ContactCreate(ContactBase):
    pass


class ContactUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    company: Optional[str] = Field(default=None, min_length=1, max_length=255)
    role: Optional[str] = Field(default=None, min_length=1, max_length=255)
    email: Optional[str] = None
    linkedin_url: Optional[str] = Field(default=None, max_length=500)
    notes: Optional[str] = None
    tags: Optional[List[str]] = None
    relationship_strength: Optional[int] = Field(default=None, ge=1, le=5)


class ContactResponse(ContactBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime


class EventBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    location: Optional[str] = Field(default=None, max_length=255)
    event_date: Optional[datetime] = None
    goals: Optional[List[str]] = None


class EventCreate(EventBase):
    pass


class EventUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = None
    location: Optional[str] = Field(default=None, max_length=255)
    event_date: Optional[datetime] = None
    goals: Optional[List[str]] = None


class EventResponse(EventBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime


class InteractionBase(BaseModel):
    contact_id: Optional[int] = None
    event_id: Optional[int] = None
    interaction_type: str = Field(..., min_length=1, max_length=100)
    notes: str = Field(..., min_length=1)
    sentiment: Optional[str] = Field(default=None, max_length=100)


class InteractionCreate(InteractionBase):
    pass


class InteractionUpdate(BaseModel):
    contact_id: Optional[int] = None
    event_id: Optional[int] = None
    interaction_type: Optional[str] = Field(default=None, min_length=1, max_length=100)
    notes: Optional[str] = Field(default=None, min_length=1)
    sentiment: Optional[str] = Field(default=None, max_length=100)


class InteractionResponse(InteractionBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    created_at: datetime


class FollowUpBase(BaseModel):
    contact_id: Optional[int] = None
    event_id: Optional[int] = None
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    status: str = Field(..., min_length=1, max_length=100)


class FollowUpCreate(FollowUpBase):
    pass


class FollowUpUpdate(BaseModel):
    contact_id: Optional[int] = None
    event_id: Optional[int] = None
    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    status: Optional[str] = Field(default=None, min_length=1, max_length=100)


class FollowUpResponse(FollowUpBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime


class UserProfileBase(BaseModel):
    full_name: Optional[str] = Field(default=None, max_length=255)
    headline: Optional[str] = Field(default=None, max_length=255)
    goals: Optional[List[str]] = None
    interests: Optional[List[str]] = None
    preferred_tone: Optional[str] = Field(default=None, max_length=100)


class UserProfileCreate(UserProfileBase):
    pass


class UserProfileUpdate(UserProfileBase):
    pass


class UserProfileResponse(UserProfileBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime


class RecommendationResponse(BaseModel):
    id: str
    recommendation_id: str
    recommendation_type: str
    title: str
    description: str
    priority_score: float
    reason: str
    related_contact_id: Optional[int] = None
    related_event_id: Optional[int] = None
    related_follow_up_id: Optional[int] = None
    created_at: datetime


class AnalyticsSummaryResponse(BaseModel):
    total_contacts: int
    total_events: int
    total_interactions: int
    total_follow_ups: int
    overdue_follow_ups_count: int
    completed_follow_ups_count: int
    upcoming_follow_ups_count: int
    cold_contacts_count: int
    average_relationship_strength: float
    interaction_frequency: float
    top_relationship_tags: List[str]
    network_health_score: float
    created_at: datetime


class FeedbackHistoryResponse(BaseModel):
    suggestion: str
    action: str
    category: Optional[str] = None
    target_type: Optional[str] = None
    target_id: Optional[str] = None
    notes: Optional[str] = None
    created_at: str


class FeedbackBucketResponse(BaseModel):
    total: int
    category_counts: dict[str, int]


class FeedbackPreferenceSignalsResponse(BaseModel):
    preferred_feedback_categories: List[str]
    tone_adjustment_signals: int
    specificity_adjustment_signals: int


class FeedbackSummaryResponse(BaseModel):
    generation_quality: FeedbackBucketResponse
    recommendation_quality: FeedbackBucketResponse
    user_preferences: FeedbackPreferenceSignalsResponse


class RecommendationTrainingDataResponse(BaseModel):
    recommendation_id: str
    recommendation_type: str
    priority_score: float
    has_contact: bool
    has_event: bool
    has_follow_up: bool
    reason: str
    label: Optional[int] = None
    feedback_category: Optional[str] = None
    created_at: datetime
