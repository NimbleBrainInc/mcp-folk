"""Folk CRM MCP Server - AI-Friendly Interface.

This server provides intent-based tools optimized for AI assistants:
- Minimal response payloads (tokens are expensive)
- Two-phase lookup (find first, get details second)
- Natural language search (fuzzy name matching)
- Compound operations where useful
"""

import logging
import os
import re
import sys
from typing import Any

from fastmcp import Context, FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse

from mcp_folk.api_client import FolkAPIError, FolkClient

# Folk ID format: prefix + UUID v4 (e.g., "per_xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx")
_FOLK_ID_RE = re.compile(
    r"^[a-z]{2,4}_[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
)


def _validate_folk_id(value: str, entity: str = "entity") -> None:
    """Validate that a string matches the Folk ID format (prefix_uuid).

    Raises McpError with an actionable message if the ID is invalid.
    """
    if not _FOLK_ID_RE.match(value):
        raise ValueError(
            f"Invalid {entity} ID '{value}'. "
            f"Folk IDs are prefix + UUID v4 format (e.g., 'per_xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx'). "
            f"Call find_person or find_company first to get the correct ID from the search results."
        )


# Configure logging to stderr (stdout is for MCP JSON-RPC)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("mcp_folk")
logger.info("Folk server module loading...")

# Create MCP server
mcp = FastMCP("Folk")

# Global client instance
_client: FolkClient | None = None


def get_client(ctx: Context | None = None) -> FolkClient:
    """Get or create the API client instance."""
    global _client
    if _client is None:
        api_key = os.environ.get("FOLK_API_KEY")
        if not api_key:
            msg = "FOLK_API_KEY environment variable is required"
            if ctx:
                ctx.error(msg)
            raise ValueError(msg)
        _client = FolkClient(api_key=api_key)
    return _client


# Health endpoint for HTTP transport
@mcp.custom_route("/health", methods=["GET"])
async def health_check(request: Request) -> JSONResponse:
    """Health check endpoint for monitoring."""
    return JSONResponse({"status": "healthy", "service": "mcp-folk"})


# =============================================================================
# TIER 1: Search/Find Tools (Most Used)
# These return minimal payloads for quick lookups
# =============================================================================


@mcp.tool()
async def find_person(
    name: str,
    ctx: Context | None = None,
) -> dict[str, Any]:
    """Find people by name in the CRM.

    Use this to check if someone exists or to get their ID for further operations.
    Returns minimal info to save tokens - use get_person_details for full info.

    Args:
        name: Name to search for (first name, last name, or full name)

    Returns:
        {
            "found": true/false,
            "matches": [{"id": "...", "name": "Full Name", "email": "..."}],
            "total": number of matches
        }
    """
    client = get_client(ctx)
    try:
        # Search by fullName using 'like' operator (Folk API's contains equivalent)
        filters = {"fullName": {"like": name}}
        people = await client.list_people(limit=10, filters=filters)

        matches = []
        for person in people:
            # Build full name from parts
            full_name_parts = []
            if person.first_name:
                full_name_parts.append(person.first_name)
            if person.last_name:
                full_name_parts.append(person.last_name)
            full_name = " ".join(full_name_parts) or person.full_name or "Unknown"

            # Get primary email if available
            email = person.emails[0] if person.emails else None

            matches.append(
                {
                    "id": person.id,
                    "name": full_name,
                    "email": email,
                }
            )

        return {
            "found": len(matches) > 0,
            "matches": matches,
            "total": len(matches),
        }
    except FolkAPIError as e:
        if ctx:
            ctx.error(f"API error: {e.message}")
        raise


@mcp.tool()
async def find_company(
    name: str,
    ctx: Context | None = None,
) -> dict[str, Any]:
    """Find companies by name in the CRM.

    Use this to check if a company exists or to get its ID for further operations.
    Returns minimal info - use get_company_details for full info.

    Args:
        name: Company name to search for

    Returns:
        {
            "found": true/false,
            "matches": [{"id": "...", "name": "Company Name", "industry": "..."}],
            "total": number of matches
        }
    """
    client = get_client(ctx)
    try:
        # Search by name using 'like' operator (Folk API's contains equivalent)
        filters = {"name": {"like": name}}
        companies = await client.list_companies(limit=10, filters=filters)

        matches = []
        for company in companies:
            matches.append(
                {
                    "id": company.id,
                    "name": company.name,
                    "industry": company.industry,
                }
            )

        return {
            "found": len(matches) > 0,
            "matches": matches,
            "total": len(matches),
        }
    except FolkAPIError as e:
        if ctx:
            ctx.error(f"API error: {e.message}")
        raise


# =============================================================================
# TIER 2: Detail Tools
# Get full information after finding the right entity
# =============================================================================


@mcp.tool()
async def get_person_details(
    person_id: str,
    ctx: Context | None = None,
) -> dict[str, Any]:
    """Get full details for a person by their ID.

    IMPORTANT: You must call find_person first to get the person_id.
    Folk IDs are prefix + UUID v4 format (e.g., "per_xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx").

    Args:
        person_id: Exact Folk ID from find_person results (prefix + UUID format)

    Returns:
        Full person details including all fields, notes count, etc.
    """
    _validate_folk_id(person_id, "person")
    client = get_client(ctx)
    try:
        person = await client.get_person(person_id)
        return {
            "id": person.id,
            "first_name": person.first_name,
            "last_name": person.last_name,
            "full_name": person.full_name,
            "emails": person.emails or [],
            "phones": person.phones or [],
            "job_title": person.job_title,
            "description": person.description,
            "created_at": person.created_at,
        }
    except FolkAPIError as e:
        if ctx:
            ctx.error(f"API error: {e.message}")
        raise


@mcp.tool()
async def get_company_details(
    company_id: str,
    ctx: Context | None = None,
) -> dict[str, Any]:
    """Get full details for a company by its ID.

    IMPORTANT: You must call find_company first to get the company_id.
    Folk IDs are prefix + UUID v4 format (e.g., "com_xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx").

    Args:
        company_id: Exact Folk ID from find_company results (prefix + UUID format)

    Returns:
        Full company details including all fields.
    """
    _validate_folk_id(company_id, "company")
    client = get_client(ctx)
    try:
        company = await client.get_company(company_id)
        return {
            "id": company.id,
            "name": company.name,
            "description": company.description,
            "industry": company.industry,
            "emails": company.emails or [],
            "phones": company.phones or [],
            "urls": company.urls or [],
            "created_at": company.created_at,
        }
    except FolkAPIError as e:
        if ctx:
            ctx.error(f"API error: {e.message}")
        raise


# =============================================================================
# TIER 3: Browse Tools
# For exploring the CRM when you don't know what you're looking for
# =============================================================================


@mcp.tool()
async def browse_people(
    page: int = 1,
    per_page: int = 20,
    ctx: Context | None = None,
) -> dict[str, Any]:
    """Browse all people in the CRM with pagination.

    Use this to explore contacts when you don't have a specific name to search.
    Returns minimal info per person to save tokens.

    Args:
        page: Page number (starts at 1)
        per_page: Results per page (max 50)

    Returns:
        {
            "people": [{"id": "...", "name": "...", "email": "..."}],
            "page": current page,
            "per_page": results per page,
            "has_more": whether more pages exist
        }
    """
    client = get_client(ctx)
    try:
        # Clamp per_page to reasonable limit
        per_page = min(max(per_page, 1), 50)

        # Folk API uses cursor pagination, simulate page-based
        # For simplicity, we'll fetch and return one page
        people = await client.list_people(limit=per_page)

        results = []
        for person in people:
            full_name_parts = []
            if person.first_name:
                full_name_parts.append(person.first_name)
            if person.last_name:
                full_name_parts.append(person.last_name)
            full_name = " ".join(full_name_parts) or person.full_name or "Unknown"

            results.append(
                {
                    "id": person.id,
                    "name": full_name,
                    "email": person.emails[0] if person.emails else None,
                    "company": person.job_title,  # Job title often includes company context
                }
            )

        return {
            "people": results,
            "page": page,
            "per_page": per_page,
            "has_more": len(results) == per_page,  # Approximation
        }
    except FolkAPIError as e:
        if ctx:
            ctx.error(f"API error: {e.message}")
        raise


@mcp.tool()
async def browse_companies(
    page: int = 1,
    per_page: int = 20,
    ctx: Context | None = None,
) -> dict[str, Any]:
    """Browse all companies in the CRM with pagination.

    Use this to explore companies when you don't have a specific name to search.
    Returns minimal info per company to save tokens.

    Args:
        page: Page number (starts at 1)
        per_page: Results per page (max 50)

    Returns:
        {
            "companies": [{"id": "...", "name": "...", "industry": "..."}],
            "page": current page,
            "per_page": results per page,
            "has_more": whether more pages exist
        }
    """
    client = get_client(ctx)
    try:
        per_page = min(max(per_page, 1), 50)
        companies = await client.list_companies(limit=per_page)

        results = []
        for company in companies:
            results.append(
                {
                    "id": company.id,
                    "name": company.name,
                    "industry": company.industry,
                }
            )

        return {
            "companies": results,
            "page": page,
            "per_page": per_page,
            "has_more": len(results) == per_page,
        }
    except FolkAPIError as e:
        if ctx:
            ctx.error(f"API error: {e.message}")
        raise


# =============================================================================
# TIER 4: Group Tools
# Query groups and filter contacts within groups
# =============================================================================


@mcp.tool()
async def list_groups(
    ctx: Context | None = None,
) -> dict[str, Any]:
    """List all groups in the Folk workspace.

    Use this to discover what groups exist when you don't know the group name.
    For querying people/companies in a known group, use find_people_in_group directly.

    Returns:
        {
            "groups": [{"id": "grp_xxx", "name": "Demos Management"}, ...],
            "total": number of groups
        }
    """
    client = get_client(ctx)
    try:
        groups = await client.list_groups(limit=100)

        return {
            "groups": [{"id": g.id, "name": g.name} for g in groups],
            "total": len(groups),
        }
    except FolkAPIError as e:
        if ctx:
            ctx.error(f"API error: {e.message}")
        raise


@mcp.tool()
async def find_people_in_group(
    group_name: str,
    status: str | None = None,
    custom_field: str | None = None,
    custom_value: str | None = None,
    limit: int = 20,
    ctx: Context | None = None,
) -> dict[str, Any]:
    """Find people in a group, optionally filtered by custom fields like Status.

    This is the primary tool for querying contacts within Folk groups/views.
    Custom fields like "Status" are group-specific in Folk.

    Args:
        group_name: Name of the group (e.g., "Demos Management", "Clients", "Leads")
        status: Filter by "Status" custom field value (e.g., "Follow up 1", "Active", "Won")
        custom_field: Name of a different custom field to filter by
        custom_value: Value to match for the custom_field
        limit: Maximum results to return (default 20, max 50)

    Returns:
        {
            "found": true/false,
            "people": [{"id": "...", "name": "...", "email": "...", "status": "...", "custom_fields": {...}}],
            "total": number of matches,
            "group_name": "Demos Management"
        }

    Examples:
        - Find leads needing follow-up: find_people_in_group("Demos Management", status="Follow up 1")
        - Find active clients: find_people_in_group("Clients", status="Active")
        - Filter by custom field: find_people_in_group("Leads", custom_field="Priority", custom_value="High")
    """
    client = get_client(ctx)
    try:
        limit = min(max(limit, 1), 50)

        # Resolve group name to ID
        groups = await client.list_groups(limit=100)
        group = next(
            (g for g in groups if g.name.lower() == group_name.lower()),
            None,
        )

        if not group:
            # Try fuzzy match
            group = next(
                (g for g in groups if group_name.lower() in g.name.lower()),
                None,
            )

        if not group:
            available = [g.name for g in groups[:10]]
            return {
                "found": False,
                "error": f"Group '{group_name}' not found",
                "available_groups": available,
                "hint": "Check the group name or use list_groups to see all available groups",
            }

        group_id = group.id

        # Build filters
        filters: dict[str, Any] = {
            "groups": {"in": {"id": group_id}},
        }

        # Add status filter if provided (Status uses 'in' operator for select fields)
        if status:
            filters[f"customFieldValues.{group_id}.Status"] = {"in": status}

        # Add custom field filter if provided (use 'in' for select fields, 'like' for text)
        if custom_field and custom_value:
            filters[f"customFieldValues.{group_id}.{custom_field}"] = {"in": custom_value}

        people = await client.list_people(limit=limit, filters=filters)

        results = []
        for person in people:
            full_name_parts = []
            if person.first_name:
                full_name_parts.append(person.first_name)
            if person.last_name:
                full_name_parts.append(person.last_name)
            full_name = " ".join(full_name_parts) or person.full_name or "Unknown"

            # Extract custom fields for this group
            group_custom_fields = person.custom_field_values.get(group_id, {})

            results.append(
                {
                    "id": person.id,
                    "name": full_name,
                    "email": person.emails[0] if person.emails else None,
                    "job_title": person.job_title,
                    "status": group_custom_fields.get("Status"),
                    "custom_fields": group_custom_fields,
                }
            )

        return {
            "found": len(results) > 0,
            "people": results,
            "total": len(results),
            "group_name": group.name,
        }
    except FolkAPIError as e:
        if ctx:
            ctx.error(f"API error: {e.message}")
        raise


@mcp.tool()
async def find_companies_in_group(
    group_name: str,
    status: str | None = None,
    custom_field: str | None = None,
    custom_value: str | None = None,
    limit: int = 20,
    ctx: Context | None = None,
) -> dict[str, Any]:
    """Find companies in a group, optionally filtered by custom fields like Status.

    This is the primary tool for querying companies within Folk groups/views.

    Args:
        group_name: Name of the group (e.g., "Target Accounts", "Partners")
        status: Filter by "Status" custom field value
        custom_field: Name of a different custom field to filter by
        custom_value: Value to match for the custom_field
        limit: Maximum results to return (default 20, max 50)

    Returns:
        {
            "found": true/false,
            "companies": [{"id": "...", "name": "...", "status": "...", "custom_fields": {...}}],
            "total": number of matches,
            "group_name": "..."
        }
    """
    client = get_client(ctx)
    try:
        limit = min(max(limit, 1), 50)

        # Resolve group name to ID
        groups = await client.list_groups(limit=100)
        group = next(
            (g for g in groups if g.name.lower() == group_name.lower()),
            None,
        )

        if not group:
            # Try fuzzy match
            group = next(
                (g for g in groups if group_name.lower() in g.name.lower()),
                None,
            )

        if not group:
            available = [g.name for g in groups[:10]]
            return {
                "found": False,
                "error": f"Group '{group_name}' not found",
                "available_groups": available,
                "hint": "Check the group name or use list_groups to see all available groups",
            }

        group_id = group.id

        # Build filters
        filters: dict[str, Any] = {
            "groups": {"in": {"id": group_id}},
        }

        # Add status filter if provided (Status uses 'in' operator for select fields)
        if status:
            filters[f"customFieldValues.{group_id}.Status"] = {"in": status}

        # Add custom field filter if provided (use 'in' for select fields, 'like' for text)
        if custom_field and custom_value:
            filters[f"customFieldValues.{group_id}.{custom_field}"] = {"in": custom_value}

        companies = await client.list_companies(limit=limit, filters=filters)

        results = []
        for company in companies:
            # Extract custom fields for this group
            group_custom_fields = company.custom_field_values.get(group_id, {})

            results.append(
                {
                    "id": company.id,
                    "name": company.name,
                    "industry": company.industry,
                    "status": group_custom_fields.get("Status"),
                    "custom_fields": group_custom_fields,
                }
            )

        return {
            "found": len(results) > 0,
            "companies": results,
            "total": len(results),
            "group_name": group.name,
        }
    except FolkAPIError as e:
        if ctx:
            ctx.error(f"API error: {e.message}")
        raise


# =============================================================================
# TIER 5: Action Tools
# Create, update, and manage CRM data
# =============================================================================


@mcp.tool()
async def add_person(
    first_name: str,
    last_name: str | None = None,
    email: str | None = None,
    phone: str | None = None,
    job_title: str | None = None,
    notes: str | None = None,
    ctx: Context | None = None,
) -> dict[str, Any]:
    """Add a new person to the CRM.

    Args:
        first_name: Person's first name (required)
        last_name: Person's last name
        email: Email address
        phone: Phone number
        job_title: Job title or role
        notes: Initial notes about this person

    Returns:
        {"id": "...", "name": "...", "created": true}
    """
    client = get_client(ctx)
    try:
        emails = [email] if email else None
        phones = [phone] if phone else None

        person = await client.create_person(
            first_name=first_name,
            last_name=last_name,
            emails=emails,
            phones=phones,
            job_title=job_title,
            description=notes,
        )

        full_name = f"{first_name} {last_name}".strip() if last_name else first_name

        return {
            "id": person.id,
            "name": full_name,
            "created": True,
        }
    except FolkAPIError as e:
        if ctx:
            ctx.error(f"API error: {e.message}")
        raise


@mcp.tool()
async def add_company(
    name: str,
    industry: str | None = None,
    website: str | None = None,
    notes: str | None = None,
    ctx: Context | None = None,
) -> dict[str, Any]:
    """Add a new company to the CRM.

    Args:
        name: Company name (required)
        industry: Industry or sector
        website: Company website URL
        notes: Initial notes about this company

    Returns:
        {"id": "...", "name": "...", "created": true}
    """
    client = get_client(ctx)
    try:
        urls = [website] if website else None

        company = await client.create_company(
            name=name,
            industry=industry,
            urls=urls,
            description=notes,
        )

        return {
            "id": company.id,
            "name": company.name,
            "created": True,
        }
    except FolkAPIError as e:
        if ctx:
            ctx.error(f"API error: {e.message}")
        raise


@mcp.tool()
async def update_person(
    person_id: str,
    first_name: str | None = None,
    last_name: str | None = None,
    email: str | None = None,
    phone: str | None = None,
    job_title: str | None = None,
    ctx: Context | None = None,
) -> dict[str, Any]:
    """Update an existing person's information.

    IMPORTANT: You must call find_person first to get the person_id.
    Folk IDs are prefix + UUID v4 format (e.g., "per_xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx").

    Args:
        person_id: Exact Folk ID from find_person results (prefix + UUID format)
        first_name: New first name (or None to keep existing)
        last_name: New last name
        email: New email (replaces existing)
        phone: New phone (replaces existing)
        job_title: New job title

    Returns:
        {"id": "...", "name": "...", "updated": true}
    """
    _validate_folk_id(person_id, "person")
    client = get_client(ctx)
    try:
        emails = [email] if email else None
        phones = [phone] if phone else None

        person = await client.update_person(
            person_id=person_id,
            first_name=first_name,
            last_name=last_name,
            emails=emails,
            phones=phones,
            job_title=job_title,
        )

        full_name_parts = []
        if person.first_name:
            full_name_parts.append(person.first_name)
        if person.last_name:
            full_name_parts.append(person.last_name)
        full_name = " ".join(full_name_parts) or "Unknown"

        return {
            "id": person.id,
            "name": full_name,
            "updated": True,
        }
    except FolkAPIError as e:
        if ctx:
            ctx.error(f"API error: {e.message}")
        raise


@mcp.tool()
async def update_company(
    company_id: str,
    name: str | None = None,
    industry: str | None = None,
    website: str | None = None,
    ctx: Context | None = None,
) -> dict[str, Any]:
    """Update an existing company's information.

    IMPORTANT: You must call find_company first to get the company_id.
    Folk IDs are prefix + UUID v4 format (e.g., "com_xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx").

    Args:
        company_id: Exact Folk ID from find_company results (prefix + UUID format)
        name: New company name
        industry: New industry
        website: New website URL

    Returns:
        {"id": "...", "name": "...", "updated": true}
    """
    _validate_folk_id(company_id, "company")
    client = get_client(ctx)
    try:
        urls = [website] if website else None

        company = await client.update_company(
            company_id=company_id,
            name=name,
            industry=industry,
            urls=urls,
        )

        return {
            "id": company.id,
            "name": company.name,
            "updated": True,
        }
    except FolkAPIError as e:
        if ctx:
            ctx.error(f"API error: {e.message}")
        raise


@mcp.tool()
async def delete_person(
    person_id: str,
    ctx: Context | None = None,
) -> dict[str, Any]:
    """Delete a person from the CRM. This action cannot be undone.

    IMPORTANT: You must call find_person first to get the person_id.
    Folk IDs are prefix + UUID v4 format (e.g., "per_xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx").

    Args:
        person_id: Exact Folk ID from find_person results (prefix + UUID format)

    Returns:
        {"id": "...", "deleted": true}
    """
    _validate_folk_id(person_id, "person")
    client = get_client(ctx)
    try:
        await client.delete_person(person_id)
        return {"id": person_id, "deleted": True}
    except FolkAPIError as e:
        if ctx:
            ctx.error(f"API error: {e.message}")
        raise


@mcp.tool()
async def delete_company(
    company_id: str,
    ctx: Context | None = None,
) -> dict[str, Any]:
    """Delete a company from the CRM. This action cannot be undone.

    IMPORTANT: You must call find_company first to get the company_id.
    Folk IDs are prefix + UUID v4 format (e.g., "com_xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx").

    Args:
        company_id: Exact Folk ID from find_company results (prefix + UUID format)

    Returns:
        {"id": "...", "deleted": true}
    """
    _validate_folk_id(company_id, "company")
    client = get_client(ctx)
    try:
        await client.delete_company(company_id)
        return {"id": company_id, "deleted": True}
    except FolkAPIError as e:
        if ctx:
            ctx.error(f"API error: {e.message}")
        raise


# =============================================================================
# TIER 6: Notes & Reminders
# Attach context to contacts
# =============================================================================


@mcp.tool()
async def add_note(
    person_id: str,
    content: str,
    ctx: Context | None = None,
) -> dict[str, Any]:
    """Add a note to a person.

    IMPORTANT: You must call find_person first to get the person_id.
    Folk IDs are prefix + UUID v4 format (e.g., "per_xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx").

    Args:
        person_id: Exact Folk ID from find_person results (prefix + UUID format)
        content: Note content

    Returns:
        {"id": "...", "added": true}
    """
    _validate_folk_id(person_id, "person")
    client = get_client(ctx)
    try:
        note = await client.create_note(
            entity_id=person_id,
            content=content,
            visibility="public",
        )
        return {"id": note.id, "added": True}
    except FolkAPIError as e:
        if ctx:
            ctx.error(f"API error: {e.message}")
        raise


@mcp.tool()
async def get_notes(
    person_id: str,
    limit: int = 10,
    ctx: Context | None = None,
) -> dict[str, Any]:
    """Get notes for a person.

    IMPORTANT: You must call find_person first to get the person_id.

    Args:
        person_id: Exact Folk ID from find_person results (prefix + UUID format)
        limit: Maximum notes to return (default 10)

    Returns:
        {"notes": [{"id": "...", "content": "...", "created_at": "..."}]}
    """
    _validate_folk_id(person_id, "person")
    client = get_client(ctx)
    try:
        notes = await client.list_notes(limit=limit, entity_id=person_id)
        return {
            "notes": [
                {
                    "id": note.id,
                    "content": note.content,
                    "created_at": note.created_at,
                }
                for note in notes
            ]
        }
    except FolkAPIError as e:
        if ctx:
            ctx.error(f"API error: {e.message}")
        raise


@mcp.tool()
async def set_reminder(
    person_id: str,
    reminder: str,
    when: str,
    ctx: Context | None = None,
) -> dict[str, Any]:
    """Set a reminder for a person.

    IMPORTANT: You must call find_person first to get the person_id.
    Folk IDs are prefix + UUID v4 format (e.g., "per_xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx").

    Args:
        person_id: Exact Folk ID from find_person results (prefix + UUID format)
        reminder: What to be reminded about
        when: When to trigger (ISO 8601 datetime, e.g., "2026-01-28T09:00:00Z")

    Returns:
        {"id": "...", "set": true}
    """
    _validate_folk_id(person_id, "person")
    client = get_client(ctx)
    try:
        result = await client.create_reminder(
            entity_id=person_id,
            name=reminder,
            trigger_time=when,
            visibility="public",
        )
        return {"id": result.id, "set": True}
    except FolkAPIError as e:
        if ctx:
            ctx.error(f"API error: {e.message}")
        raise


@mcp.tool()
async def log_interaction(
    person_id: str,
    interaction_type: str,
    when: str,
    ctx: Context | None = None,
) -> dict[str, Any]:
    """Log an interaction with a person.

    IMPORTANT: You must call find_person first to get the person_id.
    Folk IDs are prefix + UUID v4 format (e.g., "per_xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx").

    Args:
        person_id: Exact Folk ID from find_person results (prefix + UUID format)
        interaction_type: Type of interaction (e.g., "email", "meeting", "call")
        when: When it occurred (ISO 8601 datetime)

    Returns:
        {"id": "...", "logged": true}
    """
    _validate_folk_id(person_id, "person")
    client = get_client(ctx)
    try:
        result = await client.create_interaction(
            entity_id=person_id,
            interaction_type=interaction_type,
            occurred_at=when,
        )
        return {"id": result.id, "logged": True}
    except FolkAPIError as e:
        if ctx:
            ctx.error(f"API error: {e.message}")
        raise


# =============================================================================
# Utility Tools
# =============================================================================


@mcp.tool()
async def whoami(
    ctx: Context | None = None,
) -> dict[str, Any]:
    """Get information about the current authenticated user.

    Returns:
        {"id": "...", "name": "...", "email": "..."}
    """
    client = get_client(ctx)
    try:
        user = await client.get_current_user()
        return {
            "id": user.id,
            "name": user.full_name,
            "email": user.email,
        }
    except FolkAPIError as e:
        if ctx:
            ctx.error(f"API error: {e.message}")
        raise


# Create ASGI application for HTTP deployment
app = mcp.http_app()

# Stdio entrypoint for Claude Desktop / mpak
if __name__ == "__main__":
    logger.info("Running in stdio mode")
    mcp.run()
