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
