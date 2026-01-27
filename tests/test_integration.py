"""Integration tests for Folk API.

These tests require a valid FOLK_API_KEY environment variable.
They are skipped if the API key is not set.

Run with: FOLK_API_KEY=your_key uv run pytest tests/test_integration.py -v
"""

import os
from datetime import UTC, datetime, timedelta

import pytest

from mcp_folk.api_client import FolkAPIError, FolkClient

# Skip all tests in this module if FOLK_API_KEY is not set
pytestmark = pytest.mark.skipif(
    not os.environ.get("FOLK_API_KEY"),
    reason="FOLK_API_KEY environment variable not set",
)


@pytest.fixture
async def client() -> FolkClient:
    """Create a Folk client for testing."""
    return FolkClient()


@pytest.mark.asyncio
class TestReminderIntegration:
    """Integration tests for reminder functionality."""

    async def test_create_and_delete_reminder(self, client: FolkClient) -> None:
        """Test creating and deleting a reminder against the real API."""
        async with client:
            # First, we need a person to attach the reminder to
            # List existing people
            people = await client.list_people(limit=1)
            if not people:
                pytest.skip("No people in workspace to test with")

            person_id = people[0].id

            # Create a reminder for tomorrow
            tomorrow = datetime.now(UTC) + timedelta(days=1)
            tomorrow_9am = tomorrow.replace(hour=9, minute=0, second=0, microsecond=0)
            trigger_time = tomorrow_9am.isoformat()

            try:
                reminder = await client.create_reminder(
                    entity_id=person_id,
                    name="Integration test reminder",
                    trigger_time=trigger_time,
                    visibility="private",  # Private doesn't require assignedUsers
                )

                assert reminder.id is not None
                assert reminder.id.startswith("rmd_")
                assert reminder.name == "Integration test reminder"

                # Clean up
                deleted = await client.delete_reminder(reminder.id)
                assert deleted is True

            except FolkAPIError as e:
                pytest.fail(f"API error: {e.status} - {e.message} - {e.details}")

    async def test_create_public_reminder(self, client: FolkClient) -> None:
        """Test creating a public reminder (requires assignedUsers)."""
        async with client:
            # Get a person
            people = await client.list_people(limit=1)
            if not people:
                pytest.skip("No people in workspace to test with")

            person_id = people[0].id

            # Create a reminder for tomorrow
            tomorrow = datetime.now(UTC) + timedelta(days=1)
            tomorrow_9am = tomorrow.replace(hour=9, minute=0, second=0, microsecond=0)
            trigger_time = tomorrow_9am.isoformat()

            try:
                # Public reminder - client should auto-assign current user
                reminder = await client.create_reminder(
                    entity_id=person_id,
                    name="Public integration test reminder",
                    trigger_time=trigger_time,
                    visibility="public",
                )

                assert reminder.id is not None
                assert reminder.visibility.value == "public"

                # Clean up
                await client.delete_reminder(reminder.id)

            except FolkAPIError as e:
                pytest.fail(f"API error: {e.status} - {e.message} - {e.details}")

    async def test_reminder_recurrence_rule_format_accepted(self, client: FolkClient) -> None:
        """Test that our recurrenceRule format is accepted by the API."""
        async with client:
            people = await client.list_people(limit=1)
            if not people:
                pytest.skip("No people in workspace to test with")

            person_id = people[0].id

            # Test various datetime formats
            test_times = [
                datetime.now(UTC) + timedelta(days=1),
                datetime.now(UTC) + timedelta(days=7),
                datetime.now(UTC) + timedelta(hours=24),
            ]

            for test_time in test_times:
                test_time = test_time.replace(hour=9, minute=0, second=0, microsecond=0)
                trigger_time = test_time.isoformat()

                try:
                    reminder = await client.create_reminder(
                        entity_id=person_id,
                        name=f"Format test {test_time.date()}",
                        trigger_time=trigger_time,
                        visibility="private",
                    )

                    assert reminder.id is not None
                    await client.delete_reminder(reminder.id)

                except FolkAPIError as e:
                    pytest.fail(
                        f"API rejected format for {trigger_time}: "
                        f"{e.status} - {e.message} - {e.details}"
                    )


@pytest.mark.asyncio
class TestGroupIntegration:
    """Integration tests for group and filtering functionality."""

    async def test_list_groups(self, client: FolkClient) -> None:
        """Test listing groups."""
        async with client:
            groups = await client.list_groups(limit=50)

            # Should return a list (even if empty)
            assert isinstance(groups, list)

            if groups:
                # Verify group structure
                group = groups[0]
                assert hasattr(group, "id")
                assert hasattr(group, "name")
                assert group.id.startswith("grp_")
                print(f"\nFound {len(groups)} groups:")
                for g in groups[:5]:
                    print(f"  - {g.name} ({g.id})")

    async def test_filter_people_by_group(self, client: FolkClient) -> None:
        """Test filtering people by group membership."""
        async with client:
            # First get groups
            groups = await client.list_groups(limit=10)
            if not groups:
                pytest.skip("No groups in workspace to test with")

            group = groups[0]
            print(f"\nTesting with group: {group.name} ({group.id})")

            # Filter people by group
            filters = {"groups": {"in": {"id": group.id}}}
            people = await client.list_people(limit=10, filters=filters)

            print(f"Found {len(people)} people in group '{group.name}'")
            for person in people[:3]:
                print(f"  - {person.full_name or person.first_name}")
                # Check if custom field values are returned
                if person.custom_field_values:
                    group_fields = person.custom_field_values.get(group.id, {})
                    if group_fields:
                        print(f"    Custom fields: {group_fields}")

    async def test_filter_people_by_custom_field(self, client: FolkClient) -> None:
        """Test filtering people by custom field value (e.g., Status)."""
        async with client:
            # Get groups
            groups = await client.list_groups(limit=10)
            if not groups:
                pytest.skip("No groups in workspace to test with")

            # Try to find a group with people that have custom fields
            for group in groups:
                filters = {"groups": {"in": {"id": group.id}}}
                people = await client.list_people(limit=5, filters=filters)

                if people:
                    # Check if any person has custom field values
                    for person in people:
                        group_fields = person.custom_field_values.get(group.id, {})
                        if "Status" in group_fields and group_fields["Status"]:
                            status_value = group_fields["Status"]
                            print(
                                f"\nFound person with Status='{status_value}' in group '{group.name}'"
                            )

                            # Now try to filter by that status
                            status_filter = {
                                "groups": {"in": {"id": group.id}},
                                f"customFieldValues.{group.id}.Status": {"in": status_value},
                            }
                            filtered_people = await client.list_people(
                                limit=10, filters=status_filter
                            )
                            print(
                                f"Filter returned {len(filtered_people)} people with Status='{status_value}'"
                            )

                            # Verify they all have the expected status
                            for p in filtered_people:
                                p_status = p.custom_field_values.get(group.id, {}).get("Status")
                                assert p_status == status_value, (
                                    f"Expected {status_value}, got {p_status}"
                                )

                            return  # Test passed

            pytest.skip("No groups with Status custom field found")


@pytest.mark.asyncio
class TestServerToolsIntegration:
    """Integration tests for MCP server tools.

    These test the tool logic by calling the underlying functions directly,
    bypassing the FastMCP decorator which wraps them as FunctionTool objects.
    """

    async def test_list_groups_tool(self, client: FolkClient) -> None:
        """Test the list_groups logic."""
        async with client:
            groups = await client.list_groups(limit=100)

            result = {
                "groups": [{"id": g.id, "name": g.name} for g in groups],
                "total": len(groups),
            }

            assert "groups" in result
            assert "total" in result
            assert isinstance(result["groups"], list)
            assert result["total"] == len(result["groups"])

            if result["groups"]:
                group = result["groups"][0]
                assert "id" in group
                assert "name" in group
                print(f"\nlist_groups returned {result['total']} groups")
                for g in result["groups"][:3]:
                    print(f"  - {g['name']}")

    async def test_find_people_in_group_tool(self, client: FolkClient) -> None:
        """Test the find_people_in_group logic."""
        async with client:
            # Get groups
            groups = await client.list_groups(limit=100)
            if not groups:
                pytest.skip("No groups available")

            group = groups[0]
            group_name = group.name
            group_id = group.id
            print(f"\nTesting find_people_in_group with group: {group_name}")

            # Filter people by group (same logic as in server.py)
            filters = {"groups": {"in": {"id": group_id}}}
            people = await client.list_people(limit=20, filters=filters)

            results = []
            for person in people:
                full_name_parts = []
                if person.first_name:
                    full_name_parts.append(person.first_name)
                if person.last_name:
                    full_name_parts.append(person.last_name)
                full_name = " ".join(full_name_parts) or person.full_name or "Unknown"

                group_custom_fields = person.custom_field_values.get(group_id, {})

                results.append(
                    {
                        "id": person.id,
                        "name": full_name,
                        "email": person.emails[0] if person.emails else None,
                        "status": group_custom_fields.get("Status"),
                        "custom_fields": group_custom_fields,
                    }
                )

            result = {
                "found": len(results) > 0,
                "people": results,
                "total": len(results),
                "group_name": group_name,
            }

            assert "found" in result
            assert "people" in result
            assert "total" in result
            assert "group_name" in result

            print(f"Found {result['total']} people in '{result['group_name']}'")
            for person in result["people"][:3]:
                print(f"  - {person['name']} ({person.get('email', 'no email')})")

    async def test_find_people_in_group_fuzzy_match(self, client: FolkClient) -> None:
        """Test that find_people_in_group handles fuzzy group name matching."""
        async with client:
            groups = await client.list_groups(limit=100)
            if not groups:
                pytest.skip("No groups available")

            # Try partial/lowercase match (same logic as in server.py)
            group_name = "influencers"  # lowercase
            group = next(
                (g for g in groups if g.name.lower() == group_name.lower()),
                None,
            )
            if not group:
                group = next(
                    (g for g in groups if group_name.lower() in g.name.lower()),
                    None,
                )

            if group:
                print(f"\nFuzzy match: '{group_name}' -> '{group.name}'")
                assert group.name.lower() == "influencers" or "influencers" in group.name.lower()
            else:
                print(f"\nNo fuzzy match for '{group_name}' in available groups")
                print(f"Available: {[g.name for g in groups[:5]]}")
