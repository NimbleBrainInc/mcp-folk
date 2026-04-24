"""Pydantic models for Folk API responses."""

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class EntityType(StrEnum):
    """Entity types in Folk."""

    PERSON = "person"
    COMPANY = "company"
    OBJECT = "object"


class Visibility(StrEnum):
    """Visibility options."""

    PUBLIC = "public"
    PRIVATE = "private"


# Common models


class UserReference(BaseModel):
    """Reference to a user."""

    id: str = Field(..., description="User ID")
    full_name: str = Field(..., alias="fullName", description="User's full name")
    email: str = Field(..., description="User's email")


class GroupReference(BaseModel):
    """Reference to a group."""

    id: str = Field(..., description="Group ID")
    name: str = Field(..., description="Group name")


class CompanyReference(BaseModel):
    """Reference to a company."""

    id: str = Field(..., description="Company ID")
    name: str = Field(..., description="Company name")


class PersonReference(BaseModel):
    """Reference to a person."""

    id: str = Field(..., description="Person ID")
    full_name: str = Field(..., alias="fullName", description="Person's full name")


class EntityReference(BaseModel):
    """Reference to an entity (person, company, or object)."""

    id: str = Field(..., description="Entity ID")
    entity_type: EntityType = Field(..., alias="entityType", description="Entity type")
    full_name: str = Field(..., alias="fullName", description="Entity name")


class InteractionMetadata(BaseModel):
    """Interaction metadata for a person or company."""

    class UserInteraction(BaseModel):
        approximate_count: int = Field(..., alias="approximateCount")
        last_interacted_at: str | None = Field(None, alias="lastInteractedAt")

    class WorkspaceInteraction(BaseModel):
        approximate_count: int = Field(..., alias="approximateCount")
        last_interacted_at: str | None = Field(None, alias="lastInteractedAt")
        last_interacted_by: list[UserReference] = Field(
            default_factory=list, alias="lastInteractedBy"
        )

    user: UserInteraction | None = None
    workspace: WorkspaceInteraction | None = None


class Pagination(BaseModel):
    """Pagination information."""

    model_config = {"populate_by_name": True}

    next_link: str | None = Field(default=None, alias="nextLink", description="URL for next page")


# Person models


class Person(BaseModel):
    """A person in Folk."""

    id: str = Field(..., description="Person ID")
    first_name: str | None = Field(None, alias="firstName", description="First name")
    last_name: str | None = Field(None, alias="lastName", description="Last name")
    full_name: str | None = Field(None, alias="fullName", description="Full name")
    description: str | None = Field(None, description="Description")
    birthday: str | None = Field(None, description="Birthday (date)")
    job_title: str | None = Field(None, alias="jobTitle", description="Job title")
    created_at: str | None = Field(None, alias="createdAt", description="Created timestamp")
    created_by: UserReference | None = Field(None, alias="createdBy", description="Created by")
    groups: list[GroupReference] = Field(default_factory=list, description="Groups")
    companies: list[CompanyReference] = Field(default_factory=list, description="Companies")
    addresses: list[str] = Field(default_factory=list, description="Addresses")
    emails: list[str] = Field(default_factory=list, description="Email addresses")
    phones: list[str] = Field(default_factory=list, description="Phone numbers")
    urls: list[str] = Field(default_factory=list, description="URLs")
    custom_field_values: dict[str, Any] = Field(
        default_factory=dict, alias="customFieldValues", description="Custom field values"
    )
    interaction_metadata: InteractionMetadata | None = Field(
        None, alias="interactionMetadata", description="Interaction metadata"
    )


class PersonListResponse(BaseModel):
    """Response for listing people."""

    class Data(BaseModel):
        items: list[Person] = Field(default_factory=list)
        pagination: Pagination = Field(default_factory=lambda: Pagination())

    data: Data


class PersonResponse(BaseModel):
    """Response for a single person."""

    data: Person


# Company models


class Company(BaseModel):
    """A company in Folk."""

    id: str = Field(..., description="Company ID")
    name: str | None = Field(None, description="Company name")
    description: str | None = Field(None, description="Description")
    funding_raised: str | None = Field(None, alias="fundingRaised", description="Funding raised")
    last_funding_date: str | None = Field(
        None, alias="lastFundingDate", description="Last funding date"
    )
    industry: str | None = Field(None, description="Industry")
    foundation_year: int | None = Field(None, alias="foundationYear", description="Foundation year")
    employee_range: str | None = Field(None, alias="employeeRange", description="Employee range")
    created_at: str | None = Field(None, alias="createdAt", description="Created timestamp")
    created_by: UserReference | None = Field(None, alias="createdBy", description="Created by")
    groups: list[GroupReference] = Field(default_factory=list, description="Groups")
    addresses: list[str] = Field(default_factory=list, description="Addresses")
    emails: list[str] = Field(default_factory=list, description="Email addresses")
    phones: list[str] = Field(default_factory=list, description="Phone numbers")
    urls: list[str] = Field(default_factory=list, description="URLs")
    custom_field_values: dict[str, Any] = Field(
        default_factory=dict, alias="customFieldValues", description="Custom field values"
    )


class CompanyListResponse(BaseModel):
    """Response for listing companies."""

    class Data(BaseModel):
        items: list[Company] = Field(default_factory=list)
        pagination: Pagination = Field(default_factory=lambda: Pagination())

    data: Data


class CompanyResponse(BaseModel):
    """Response for a single company."""

    data: Company


# Note models


class NoteAuthor(BaseModel):
    """Author of a note (user or assistant)."""

    id: str | None = Field(None, description="Author ID")
    full_name: str | None = Field(None, alias="fullName", description="Author name")
    email: str | None = Field(None, description="Author email")


class Note(BaseModel):
    """A note in Folk."""

    id: str = Field(..., description="Note ID")
    entity: EntityReference | None = Field(None, description="Related entity")
    content: str = Field(..., description="Note content")
    visibility: Visibility = Field(default=Visibility.PUBLIC, description="Visibility")
    author: NoteAuthor | None = Field(None, description="Note author")
    created_at: str | None = Field(None, alias="createdAt", description="Created timestamp")
    parent_note: dict[str, Any] | None = Field(
        None, alias="parentNote", description="Parent note reference"
    )


class NoteListResponse(BaseModel):
    """Response for listing notes."""

    class Data(BaseModel):
        items: list[Note] = Field(default_factory=list)
        pagination: Pagination = Field(default_factory=lambda: Pagination())

    data: Data


class NoteResponse(BaseModel):
    """Response for a single note."""

    data: Note


# Reminder models


class Reminder(BaseModel):
    """A reminder in Folk."""

    id: str = Field(..., description="Reminder ID")
    name: str = Field(..., description="Reminder name")
    entity: EntityReference | None = Field(None, description="Related entity")
    recurrence_rule: str | None = Field(
        None, alias="recurrenceRule", description="iCalendar recurrence rule"
    )
    visibility: Visibility = Field(default=Visibility.PUBLIC, description="Visibility")
    assigned_users: list[UserReference] = Field(
        default_factory=list, alias="assignedUsers", description="Assigned users"
    )
    next_trigger_time: str | None = Field(
        None, alias="nextTriggerTime", description="Next trigger time"
    )
    last_trigger_time: str | None = Field(
        None, alias="lastTriggerTime", description="Last trigger time"
    )
    created_by: UserReference | None = Field(None, alias="createdBy", description="Created by")
    created_at: str | None = Field(None, alias="createdAt", description="Created timestamp")


class ReminderListResponse(BaseModel):
    """Response for listing reminders."""

    class Data(BaseModel):
        items: list[Reminder] = Field(default_factory=list)
        pagination: Pagination = Field(default_factory=lambda: Pagination())

    data: Data


class ReminderResponse(BaseModel):
    """Response for a single reminder."""

    data: Reminder


# Group models


class Group(BaseModel):
    """A group in Folk."""

    id: str = Field(..., description="Group ID")
    name: str = Field(..., description="Group name")


class GroupListResponse(BaseModel):
    """Response for listing groups."""

    class Data(BaseModel):
        items: list[Group] = Field(default_factory=list)
        pagination: Pagination = Field(default_factory=lambda: Pagination())

    data: Data


# User models


class User(BaseModel):
    """A user in Folk."""

    id: str = Field(..., description="User ID")
    full_name: str = Field(..., alias="fullName", description="User's full name")
    email: str = Field(..., description="User's email")


class UserListResponse(BaseModel):
    """Response for listing users."""

    class Data(BaseModel):
        items: list[User] = Field(default_factory=list)
        pagination: Pagination = Field(default_factory=lambda: Pagination())

    data: Data


class UserResponse(BaseModel):
    """Response for a single user."""

    data: User


# Deal models


class Deal(BaseModel):
    """A deal in Folk."""

    id: str = Field(..., description="Deal ID")
    name: str = Field(..., description="Deal name")
    companies: list[CompanyReference] = Field(default_factory=list, description="Companies")
    people: list[PersonReference] = Field(default_factory=list, description="People")
    created_at: str | None = Field(None, alias="createdAt", description="Created timestamp")
    created_by: UserReference | None = Field(None, alias="createdBy", description="Created by")
    custom_field_values: dict[str, Any] = Field(
        default_factory=dict, alias="customFieldValues", description="Custom field values"
    )


class DealListResponse(BaseModel):
    """Response for listing deals."""

    class Data(BaseModel):
        items: list[Deal] = Field(default_factory=list)
        pagination: Pagination = Field(default_factory=lambda: Pagination())

    data: Data
    deprecations: list[str] = Field(default_factory=list)


# Interaction models


class Interaction(BaseModel):
    """An interaction in Folk."""

    id: str = Field(..., description="Interaction ID")
    entity_id: str = Field(..., alias="entityId", description="Entity ID")
    interaction_type: str = Field(..., alias="interactionType", description="Interaction type")
    occurred_at: str = Field(..., alias="occurredAt", description="When interaction occurred")


class InteractionResponse(BaseModel):
    """Response for creating an interaction."""

    data: Interaction


# Error models


class ErrorDetail(BaseModel):
    """Error detail."""

    code: str | None = Field(None, description="Error code")
    message: str | None = Field(None, description="Error message")
    documentation_url: str | None = Field(None, alias="documentationUrl", description="Doc URL")
    request_id: str | None = Field(None, alias="requestId", description="Request ID")
    timestamp: str | None = Field(None, description="Timestamp")


class ErrorResponse(BaseModel):
    """Error response from Folk API."""

    error: ErrorDetail | None = None
