"""Async HTTP client for Folk API."""

import os
from typing import Any

import aiohttp
from aiohttp import ClientError

from .api_models import (
    Company,
    CompanyListResponse,
    CompanyResponse,
    Deal,
    DealListResponse,
    Group,
    GroupListResponse,
    Interaction,
    InteractionResponse,
    Note,
    NoteListResponse,
    NoteResponse,
    Person,
    PersonListResponse,
    PersonResponse,
    Reminder,
    ReminderListResponse,
    ReminderResponse,
    User,
    UserListResponse,
    UserResponse,
)


class FolkAPIError(Exception):
    """Exception raised for Folk API errors."""

    def __init__(self, status: int, message: str, details: dict[str, Any] | None = None) -> None:
        self.status = status
        self.message = message
        self.details = details
        super().__init__(f"Folk API Error {status}: {message}")


class FolkClient:
    """Async client for Folk API."""

    BASE_URL = "https://api.folk.app/v1"

    def __init__(
        self,
        api_key: str | None = None,
        timeout: float = 30.0,
    ) -> None:
        self.api_key = api_key or os.environ.get("FOLK_API_KEY")
        if not self.api_key:
            raise ValueError("FOLK_API_KEY is required")
        self.timeout = timeout
        self._session: aiohttp.ClientSession | None = None

    async def __aenter__(self) -> "FolkClient":
        await self._ensure_session()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.close()

    async def _ensure_session(self) -> None:
        if not self._session:
            headers = {
                "User-Agent": "mcp-server-folk/0.1.0",
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            }

            self._session = aiohttp.ClientSession(
                headers=headers, timeout=aiohttp.ClientTimeout(total=self.timeout)
            )

    async def close(self) -> None:
        """Close the HTTP session."""
        if self._session:
            await self._session.close()
            self._session = None

    async def _request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
        json_data: Any | None = None,
    ) -> dict[str, Any]:
        """Make an HTTP request to the Folk API."""
        await self._ensure_session()

        url = f"{self.BASE_URL}{path}"

        # Clean up params (remove None values)
        if params:
            params = {k: v for k, v in params.items() if v is not None}

        try:
            if not self._session:
                raise RuntimeError("Session not initialized")

            kwargs: dict[str, Any] = {}
            if json_data is not None:
                kwargs["json"] = json_data
            if params:
                kwargs["params"] = params

            async with self._session.request(method, url, **kwargs) as response:
                result = await response.json()

                if response.status >= 400:
                    error_msg = "Unknown error"
                    if isinstance(result, dict):
                        if "error" in result:
                            error_obj = result["error"]
                            if isinstance(error_obj, dict):
                                error_msg = error_obj.get("message", str(error_obj))
                            else:
                                error_msg = str(error_obj)
                        elif "message" in result:
                            error_msg = result["message"]

                    raise FolkAPIError(response.status, error_msg, result)

                return result  # type: ignore[no-any-return]

        except ClientError as e:
            raise FolkAPIError(500, f"Network error: {str(e)}") from e

    # People endpoints

    async def list_people(
        self,
        limit: int = 20,
        cursor: str | None = None,
        combinator: str = "and",
        filters: dict[str, Any] | None = None,
    ) -> list[Person]:
        """List people in the workspace."""
        params: dict[str, Any] = {
            "limit": limit,
            "cursor": cursor,
            "combinator": combinator,
        }

        # Add filter params (serialize nested dicts to bracket notation)
        if filters:
            for key, value in filters.items():
                if isinstance(value, dict):
                    for op, op_value in value.items():
                        params[f"filter[{key}][{op}]"] = op_value
                else:
                    params[f"filter[{key}]"] = value

        data = await self._request("GET", "/people", params=params)
        response = PersonListResponse(**data)
        return response.data.items

    async def get_person(self, person_id: str) -> Person:
        """Get a specific person by ID."""
        data = await self._request("GET", f"/people/{person_id}")
        response = PersonResponse(**data)
        return response.data

    async def create_person(
        self,
        first_name: str | None = None,
        last_name: str | None = None,
        emails: list[str] | None = None,
        phones: list[str] | None = None,
        job_title: str | None = None,
        description: str | None = None,
        group_ids: list[str] | None = None,
        company_ids: list[str] | None = None,
        custom_fields: dict[str, Any] | None = None,
    ) -> Person:
        """Create a new person."""
        body: dict[str, Any] = {}

        if first_name:
            body["firstName"] = first_name
        if last_name:
            body["lastName"] = last_name
        if emails:
            body["emails"] = emails
        if phones:
            body["phones"] = phones
        if job_title:
            body["jobTitle"] = job_title
        if description:
            body["description"] = description
        if group_ids:
            body["groupIds"] = group_ids
        if company_ids:
            body["companyIds"] = company_ids
        if custom_fields:
            body["customFieldValues"] = custom_fields

        data = await self._request("POST", "/people", json_data=body)
        response = PersonResponse(**data)
        return response.data

    async def update_person(
        self,
        person_id: str,
        first_name: str | None = None,
        last_name: str | None = None,
        emails: list[str] | None = None,
        phones: list[str] | None = None,
        job_title: str | None = None,
        description: str | None = None,
        group_ids: list[str] | None = None,
        company_ids: list[str] | None = None,
        custom_fields: dict[str, Any] | None = None,
    ) -> Person:
        """Update a person."""
        body: dict[str, Any] = {}

        if first_name is not None:
            body["firstName"] = first_name
        if last_name is not None:
            body["lastName"] = last_name
        if emails is not None:
            body["emails"] = emails
        if phones is not None:
            body["phones"] = phones
        if job_title is not None:
            body["jobTitle"] = job_title
        if description is not None:
            body["description"] = description
        if group_ids is not None:
            body["groupIds"] = group_ids
        if company_ids is not None:
            body["companyIds"] = company_ids
        if custom_fields is not None:
            body["customFieldValues"] = custom_fields

        data = await self._request("PATCH", f"/people/{person_id}", json_data=body)
        response = PersonResponse(**data)
        return response.data

    async def delete_person(self, person_id: str) -> bool:
        """Delete a person."""
        await self._request("DELETE", f"/people/{person_id}")
        return True

    # Company endpoints

    async def list_companies(
        self,
        limit: int = 20,
        cursor: str | None = None,
        combinator: str = "and",
        filters: dict[str, Any] | None = None,
    ) -> list[Company]:
        """List companies in the workspace."""
        params: dict[str, Any] = {
            "limit": limit,
            "cursor": cursor,
            "combinator": combinator,
        }

        # Add filter params (serialize nested dicts to bracket notation)
        if filters:
            for key, value in filters.items():
                if isinstance(value, dict):
                    for op, op_value in value.items():
                        params[f"filter[{key}][{op}]"] = op_value
                else:
                    params[f"filter[{key}]"] = value

        data = await self._request("GET", "/companies", params=params)
        response = CompanyListResponse(**data)
        return response.data.items

    async def get_company(self, company_id: str) -> Company:
        """Get a specific company by ID."""
        data = await self._request("GET", f"/companies/{company_id}")
        response = CompanyResponse(**data)
        return response.data

    async def create_company(
        self,
        name: str,
        description: str | None = None,
        industry: str | None = None,
        emails: list[str] | None = None,
        phones: list[str] | None = None,
        urls: list[str] | None = None,
        group_ids: list[str] | None = None,
        custom_fields: dict[str, Any] | None = None,
    ) -> Company:
        """Create a new company."""
        body: dict[str, Any] = {"name": name}

        if description:
            body["description"] = description
        if industry:
            body["industry"] = industry
        if emails:
            body["emails"] = emails
        if phones:
            body["phones"] = phones
        if urls:
            body["urls"] = urls
        if group_ids:
            body["groupIds"] = group_ids
        if custom_fields:
            body["customFieldValues"] = custom_fields

        data = await self._request("POST", "/companies", json_data=body)
        response = CompanyResponse(**data)
        return response.data

    async def update_company(
        self,
        company_id: str,
        name: str | None = None,
        description: str | None = None,
        industry: str | None = None,
        emails: list[str] | None = None,
        phones: list[str] | None = None,
        urls: list[str] | None = None,
        group_ids: list[str] | None = None,
        custom_fields: dict[str, Any] | None = None,
    ) -> Company:
        """Update a company."""
        body: dict[str, Any] = {}

        if name is not None:
            body["name"] = name
        if description is not None:
            body["description"] = description
        if industry is not None:
            body["industry"] = industry
        if emails is not None:
            body["emails"] = emails
        if phones is not None:
            body["phones"] = phones
        if urls is not None:
            body["urls"] = urls
        if group_ids is not None:
            body["groupIds"] = group_ids
        if custom_fields is not None:
            body["customFieldValues"] = custom_fields

        data = await self._request("PATCH", f"/companies/{company_id}", json_data=body)
        response = CompanyResponse(**data)
        return response.data

    async def delete_company(self, company_id: str) -> bool:
        """Delete a company."""
        await self._request("DELETE", f"/companies/{company_id}")
        return True

    # Note endpoints

    async def list_notes(
        self,
        limit: int = 20,
        cursor: str | None = None,
        entity_id: str | None = None,
    ) -> list[Note]:
        """List notes in the workspace."""
        params: dict[str, Any] = {
            "limit": limit,
            "cursor": cursor,
        }
        if entity_id:
            params["entity.id"] = entity_id

        data = await self._request("GET", "/notes", params=params)
        response = NoteListResponse(**data)
        return response.data.items

    async def get_note(self, note_id: str) -> Note:
        """Get a specific note by ID."""
        data = await self._request("GET", f"/notes/{note_id}")
        response = NoteResponse(**data)
        return response.data

    async def create_note(
        self,
        entity_id: str,
        content: str,
        visibility: str = "public",
    ) -> Note:
        """Create a new note."""
        body: dict[str, Any] = {
            "entity": {"id": entity_id},
            "content": content,
            "visibility": visibility,
        }

        data = await self._request("POST", "/notes", json_data=body)
        response = NoteResponse(**data)
        return response.data

    async def update_note(
        self,
        note_id: str,
        content: str | None = None,
        visibility: str | None = None,
    ) -> Note:
        """Update a note."""
        body: dict[str, Any] = {}

        if content is not None:
            body["content"] = content
        if visibility is not None:
            body["visibility"] = visibility

        data = await self._request("PATCH", f"/notes/{note_id}", json_data=body)
        response = NoteResponse(**data)
        return response.data

    async def delete_note(self, note_id: str) -> bool:
        """Delete a note."""
        await self._request("DELETE", f"/notes/{note_id}")
        return True

    # Reminder endpoints

    async def list_reminders(
        self,
        limit: int = 20,
        cursor: str | None = None,
        entity_id: str | None = None,
    ) -> list[Reminder]:
        """List reminders in the workspace."""
        params: dict[str, Any] = {
            "limit": limit,
            "cursor": cursor,
        }
        if entity_id:
            params["entity.id"] = entity_id

        data = await self._request("GET", "/reminders", params=params)
        response = ReminderListResponse(**data)
        return response.data.items

    async def get_reminder(self, reminder_id: str) -> Reminder:
        """Get a specific reminder by ID."""
        data = await self._request("GET", f"/reminders/{reminder_id}")
        response = ReminderResponse(**data)
        return response.data

    async def create_reminder(
        self,
        entity_id: str,
        name: str,
        trigger_time: str,
        visibility: str = "public",
        assigned_user_ids: list[str] | None = None,
    ) -> Reminder:
        """Create a new reminder.

        Args:
            entity_id: The entity ID to attach the reminder to
            name: Reminder name/description
            trigger_time: ISO 8601 datetime (e.g., "2026-01-15T09:00:00Z")
            visibility: "public" or "private"
            assigned_user_ids: Optional list of user IDs to assign
        """
        # Convert ISO datetime to iCalendar RRULE format
        # Folk API requires recurrenceRule in iCalendar format
        from datetime import datetime

        # Parse the ISO datetime
        dt = datetime.fromisoformat(trigger_time.replace("Z", "+00:00"))
        # Format as iCalendar DTSTART (use UTC)
        dtstart = dt.strftime("%Y%m%dT%H%M%S")
        # Create a one-time reminder (COUNT=1)
        recurrence_rule = f"DTSTART;TZID=UTC:{dtstart}\nRRULE:FREQ=DAILY;COUNT=1"

        body: dict[str, Any] = {
            "entity": {"id": entity_id},
            "name": name,
            "recurrenceRule": recurrence_rule,
            "visibility": visibility,
        }

        if assigned_user_ids:
            body["assignedUsers"] = [{"id": uid} for uid in assigned_user_ids]

        data = await self._request("POST", "/reminders", json_data=body)
        response = ReminderResponse(**data)
        return response.data

    async def update_reminder(
        self,
        reminder_id: str,
        name: str | None = None,
        trigger_time: str | None = None,
        visibility: str | None = None,
        recurrence_rule: str | None = None,
        assigned_user_ids: list[str] | None = None,
    ) -> Reminder:
        """Update a reminder."""
        body: dict[str, Any] = {}

        if name is not None:
            body["name"] = name
        if trigger_time is not None:
            body["triggerTime"] = trigger_time
        if visibility is not None:
            body["visibility"] = visibility
        if recurrence_rule is not None:
            body["recurrenceRule"] = recurrence_rule
        if assigned_user_ids is not None:
            body["assignedUserIds"] = assigned_user_ids

        data = await self._request("PATCH", f"/reminders/{reminder_id}", json_data=body)
        response = ReminderResponse(**data)
        return response.data

    async def delete_reminder(self, reminder_id: str) -> bool:
        """Delete a reminder."""
        await self._request("DELETE", f"/reminders/{reminder_id}")
        return True

    # Group endpoints

    async def list_groups(
        self,
        limit: int = 20,
        cursor: str | None = None,
    ) -> list[Group]:
        """List groups in the workspace."""
        params: dict[str, Any] = {
            "limit": limit,
            "cursor": cursor,
        }

        data = await self._request("GET", "/groups", params=params)
        response = GroupListResponse(**data)
        return response.data.items

    # User endpoints

    async def list_users(
        self,
        limit: int = 20,
        cursor: str | None = None,
    ) -> list[User]:
        """List users in the workspace."""
        params: dict[str, Any] = {
            "limit": limit,
            "cursor": cursor,
        }

        data = await self._request("GET", "/users", params=params)
        response = UserListResponse(**data)
        return response.data.items

    async def get_current_user(self) -> User:
        """Get the current user."""
        data = await self._request("GET", "/users/me")
        response = UserResponse(**data)
        return response.data

    async def get_user(self, user_id: str) -> User:
        """Get a specific user by ID."""
        data = await self._request("GET", f"/users/{user_id}")
        response = UserResponse(**data)
        return response.data

    # Deal endpoints

    async def list_deals(
        self,
        group_id: str,
        object_type: str,
        limit: int = 20,
        cursor: str | None = None,
        combinator: str = "and",
        filters: dict[str, Any] | None = None,
    ) -> list[Deal]:
        """List deals in a group."""
        params: dict[str, Any] = {
            "limit": limit,
            "cursor": cursor,
            "combinator": combinator,
        }

        # Add filter params (serialize nested dicts to bracket notation)
        if filters:
            for key, value in filters.items():
                if isinstance(value, dict):
                    for op, op_value in value.items():
                        params[f"filter[{key}][{op}]"] = op_value
                else:
                    params[f"filter[{key}]"] = value

        data = await self._request("GET", f"/groups/{group_id}/{object_type}", params=params)
        response = DealListResponse(**data)
        return response.data.items

    # Interaction endpoints

    async def create_interaction(
        self,
        entity_id: str,
        interaction_type: str,
        occurred_at: str,
    ) -> Interaction:
        """Create a new interaction."""
        body: dict[str, Any] = {
            "entity": {"id": entity_id},
            "interactionType": interaction_type,
            "occurredAt": occurred_at,
        }

        data = await self._request("POST", "/interactions", json_data=body)
        response = InteractionResponse(**data)
        return response.data
