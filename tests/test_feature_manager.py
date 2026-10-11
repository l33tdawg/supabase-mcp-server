"""Tests for FeatureManager access checks.

This fork fails open when the licence service cannot be reached, so that the
dead upstream service at api.thequery.dev can never block a tool call. An
explicit denial from a reachable service is still honoured.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from supabase_mcp.clients.api_client import ApiClient, FeatureAccessResponse
from supabase_mcp.core.feature_manager import FeatureManager
from supabase_mcp.exceptions import APIConnectionError, FeatureAccessError


@pytest.fixture
def feature_manager() -> FeatureManager:
    """A FeatureManager wired to a mocked API client."""
    return FeatureManager(api_client=MagicMock(spec=ApiClient))


class TestCheckFeatureAccessFailOpen:
    """check_feature_access must not block tool calls when the service is down."""

    async def test_grants_when_service_is_unreachable(self, feature_manager: FeatureManager) -> None:
        """An unreachable licence service grants access instead of raising."""
        feature_manager.api_client.check_feature_access = AsyncMock(
            side_effect=APIConnectionError("Network error after 3 retry attempts", status_code=None)
        )

        # Must not raise: the tool proceeds.
        assert await feature_manager.check_feature_access("get_schemas") is None

    async def test_grants_on_unexpected_error(self, feature_manager: FeatureManager) -> None:
        """Any unexpected failure also fails open rather than bricking the server."""
        feature_manager.api_client.check_feature_access = AsyncMock(side_effect=RuntimeError("boom"))

        assert await feature_manager.check_feature_access("get_schemas") is None

    async def test_granted_response_passes_through(self, feature_manager: FeatureManager) -> None:
        """A reachable service that grants access is a no-op."""
        feature_manager.api_client.check_feature_access = AsyncMock(
            return_value=FeatureAccessResponse(access_granted=True)
        )

        assert await feature_manager.check_feature_access("get_schemas") is None

    async def test_explicit_denial_is_still_honoured(self, feature_manager: FeatureManager) -> None:
        """A reachable service that denies access still raises."""
        feature_manager.api_client.check_feature_access = AsyncMock(
            return_value=FeatureAccessResponse(access_granted=False)
        )

        with pytest.raises(FeatureAccessError):
            await feature_manager.check_feature_access("get_schemas")
