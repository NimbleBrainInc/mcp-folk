"""Tests for Folk API client."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcp_folk.api_client import FolkClient


class TestReminderRecurrenceRule:
    """Tests for reminder recurrenceRule format generation."""

    def test_recurrence_rule_format_utc(self) -> None:
        """Test that recurrenceRule uses TZID=UTC format, not Z suffix on datetime."""
        # The Folk API requires: DTSTART;TZID=UTC:20260115T090000
        # NOT: DTSTART:20260115T090000Z (Z suffix on datetime is wrong)
        trigger_time = "2026-01-15T09:00:00Z"

        # Parse the same way the client does
        dt = datetime.fromisoformat(trigger_time.replace("Z", "+00:00"))
        dt_utc = dt.astimezone(UTC)
        dtstart = dt_utc.strftime("%Y%m%dT%H%M%S")
        recurrence_rule = f"DTSTART;TZID=UTC:{dtstart}\nRRULE:COUNT=1"

        # Verify format
        assert "DTSTART;TZID=UTC:" in recurrence_rule
        # Datetime should NOT end with Z suffix (Z is OK in TZID=UTC)
        assert not recurrence_rule.endswith("Z")
        assert "T090000Z" not in recurrence_rule  # No Z suffix on datetime
        assert "\nRRULE:COUNT=1" in recurrence_rule
        assert "20260115T090000" in recurrence_rule

    def test_recurrence_rule_one_time_no_freq(self) -> None:
        """Test that one-time reminders use COUNT=1 without FREQ."""
        # Folk API docs: No repeat = RRULE:COUNT=1
        # NOT: RRULE:FREQ=DAILY;COUNT=1
        trigger_time = "2026-01-15T09:00:00Z"

        dt = datetime.fromisoformat(trigger_time.replace("Z", "+00:00"))
        dt_utc = dt.astimezone(UTC)
        dtstart = dt_utc.strftime("%Y%m%dT%H%M%S")
        recurrence_rule = f"DTSTART;TZID=UTC:{dtstart}\nRRULE:COUNT=1"

        assert "FREQ=" not in recurrence_rule
        assert "RRULE:COUNT=1" in recurrence_rule

    def test_recurrence_rule_with_timezone_offset(self) -> None:
        """Test that timezone offsets are converted to UTC correctly."""
        # Input in PST (UTC-8)
        trigger_time = "2026-01-15T09:00:00-08:00"

        dt = datetime.fromisoformat(trigger_time)
        dt_utc = dt.astimezone(UTC)
        dtstart = dt_utc.strftime("%Y%m%dT%H%M%S")
        recurrence_rule = f"DTSTART;TZID=UTC:{dtstart}\nRRULE:COUNT=1"

        # 09:00 PST = 17:00 UTC
        assert "20260115T170000" in recurrence_rule

    def test_recurrence_rule_format_matches_folk_api(self) -> None:
        """Test that format matches Folk API documentation example."""
        # Folk API example: DTSTART;TZID=Europe/Paris:20250717T090000\nRRULE:FREQ=WEEKLY;INTERVAL=1
        # Our format for one-time: DTSTART;TZID=UTC:20260115T090000\nRRULE:COUNT=1
        trigger_time = "2026-01-15T09:00:00Z"

        dt = datetime.fromisoformat(trigger_time.replace("Z", "+00:00"))
        dt_utc = dt.astimezone(UTC)
        dtstart = dt_utc.strftime("%Y%m%dT%H%M%S")
        recurrence_rule = f"DTSTART;TZID=UTC:{dtstart}\nRRULE:COUNT=1"

        # Check structure matches: DTSTART;TZID=<tz>:<datetime>\nRRULE:<params>
        parts = recurrence_rule.split("\n")
        assert len(parts) == 2
        assert parts[0].startswith("DTSTART;TZID=")
        assert parts[1].startswith("RRULE:")


@pytest.mark.asyncio
class TestCreateReminderIntegration:
    """Integration-style tests for create_reminder method."""

    async def test_create_reminder_request_body(self) -> None:
        """Test that create_reminder sends correct request body format."""
        with patch.object(FolkClient, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {
                "data": {
                    "id": "rem_123",
                    "name": "Test reminder",
                    "visibility": "private",
                    "assignedUsers": [],
                }
            }

            client = FolkClient(api_key="test_key")
            await client.create_reminder(
                entity_id="per_456",
                name="Test reminder",
                trigger_time="2026-01-15T09:00:00Z",
                visibility="private",
            )

            # Verify the request was made with correct body
            mock_request.assert_called_once()
            call_args = mock_request.call_args
            assert call_args[0][0] == "POST"
            assert call_args[0][1] == "/reminders"

            body = call_args[1]["json_data"]
            assert body["entity"] == {"id": "per_456"}
            assert body["name"] == "Test reminder"
            assert body["visibility"] == "private"
            assert "DTSTART;TZID=UTC:" in body["recurrenceRule"]
            assert "\nRRULE:COUNT=1" in body["recurrenceRule"]
            # Private reminders don't need assignedUsers
            assert "assignedUsers" not in body

    async def test_create_public_reminder_auto_assigns_user(self) -> None:
        """Test that public reminders auto-assign current user."""
        with (
            patch.object(FolkClient, "_request", new_callable=AsyncMock) as mock_request,
            patch.object(FolkClient, "get_current_user", new_callable=AsyncMock) as mock_user,
        ):
            # Mock current user response
            mock_user_obj = MagicMock()
            mock_user_obj.id = "usr_789"
            mock_user.return_value = mock_user_obj

            mock_request.return_value = {
                "data": {
                    "id": "rem_123",
                    "name": "Test reminder",
                    "visibility": "public",
                    "assignedUsers": [
                        {"id": "usr_789", "fullName": "Test User", "email": "test@example.com"}
                    ],
                }
            }

            client = FolkClient(api_key="test_key")
            await client.create_reminder(
                entity_id="per_456",
                name="Test reminder",
                trigger_time="2026-01-15T09:00:00Z",
                visibility="public",
            )

            # Verify current user was fetched
            mock_user.assert_called_once()

            # Verify assignedUsers was included in request
            body = mock_request.call_args[1]["json_data"]
            assert body["assignedUsers"] == [{"id": "usr_789"}]

    async def test_create_public_reminder_with_explicit_users(self) -> None:
        """Test that explicit assignedUsers skips auto-assignment."""
        with (
            patch.object(FolkClient, "_request", new_callable=AsyncMock) as mock_request,
            patch.object(FolkClient, "get_current_user", new_callable=AsyncMock) as mock_user,
        ):
            mock_request.return_value = {
                "data": {
                    "id": "rem_123",
                    "name": "Test reminder",
                    "visibility": "public",
                    "assignedUsers": [
                        {
                            "id": "usr_explicit",
                            "fullName": "Explicit User",
                            "email": "explicit@example.com",
                        }
                    ],
                }
            }

            client = FolkClient(api_key="test_key")
            await client.create_reminder(
                entity_id="per_456",
                name="Test reminder",
                trigger_time="2026-01-15T09:00:00Z",
                visibility="public",
                assigned_user_ids=["usr_explicit"],
            )

            # Current user should NOT be fetched when explicit users provided
            mock_user.assert_not_called()

            # Verify explicit users were used in request
            body = mock_request.call_args[1]["json_data"]
            assert body["assignedUsers"] == [{"id": "usr_explicit"}]

    async def test_create_reminder_datetime_formats(self) -> None:
        """Test various datetime formats are handled correctly."""
        test_cases = [
            ("2026-01-15T09:00:00Z", "20260115T090000"),
            ("2026-01-15T09:00:00+00:00", "20260115T090000"),
            ("2026-01-15T17:00:00+08:00", "20260115T090000"),  # +8 to UTC
            ("2026-01-15T01:00:00-08:00", "20260115T090000"),  # -8 to UTC
        ]

        for trigger_time, expected_dtstart in test_cases:
            with patch.object(FolkClient, "_request", new_callable=AsyncMock) as mock_request:
                mock_request.return_value = {
                    "data": {
                        "id": "rem_123",
                        "name": "Test",
                        "visibility": "private",
                        "assignedUsers": [],
                    }
                }

                client = FolkClient(api_key="test_key")
                await client.create_reminder(
                    entity_id="per_456",
                    name="Test",
                    trigger_time=trigger_time,
                    visibility="private",
                )

                body = mock_request.call_args[1]["json_data"]
                assert expected_dtstart in body["recurrenceRule"], (
                    f"Failed for {trigger_time}: expected {expected_dtstart} in {body['recurrenceRule']}"
                )
