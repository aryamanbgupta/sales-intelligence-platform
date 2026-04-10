"""Tests for research.research_contractor and research.research_batch.

Mocks the AsyncOpenAI client to avoid real API calls.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.pipeline.research import (
    BatchResearchReport,
    ResearchResult,
    research_batch,
    research_contractor,
)


def _make_mock_response(content="Research text here.", citations=None):
    """Build a mock OpenAI chat completion response."""
    message = MagicMock()
    message.content = content

    choice = MagicMock()
    choice.message = message

    response = MagicMock()
    response.choices = [choice]
    response.citations = citations or ["https://source.com"]
    return response


def _make_mock_client(response=None, side_effect=None):
    """Build a mock AsyncOpenAI client."""
    client = AsyncMock()
    if side_effect:
        client.chat.completions.create = AsyncMock(side_effect=side_effect)
    else:
        client.chat.completions.create = AsyncMock(
            return_value=response or _make_mock_response()
        )
    return client


@pytest.mark.asyncio
class TestResearchContractor:

    async def test_success(self):
        client = _make_mock_client()
        contractor = {"name": "Test Co", "city": "NYC", "state": "NY"}

        result = await research_contractor(client, contractor, contractor_id=1)

        assert result.success is True
        assert result.contractor_id == 1
        assert result.contractor_name == "Test Co"
        assert "Research text here." in result.research_summary
        assert len(result.citations) > 0
        assert result.duration_seconds > 0

    async def test_retries_on_rate_limit(self):
        from openai import RateLimitError

        error_resp = MagicMock()
        error_resp.status_code = 429
        error_resp.headers = {}

        rate_error = RateLimitError(
            message="Rate limited",
            response=error_resp,
            body=None,
        )

        client = _make_mock_client(
            side_effect=[rate_error, _make_mock_response("Retry success")]
        )
        contractor = {"name": "Retry Co"}

        with patch("app.pipeline.research.asyncio.sleep", new_callable=AsyncMock):
            result = await research_contractor(client, contractor, contractor_id=2)

        assert result.success is True
        assert "Retry success" in result.research_summary
        assert client.chat.completions.create.call_count == 2

    async def test_fails_after_max_retries(self):
        from openai import RateLimitError

        error_resp = MagicMock()
        error_resp.status_code = 429
        error_resp.headers = {}

        rate_error = RateLimitError(
            message="Rate limited",
            response=error_resp,
            body=None,
        )

        client = _make_mock_client(side_effect=[rate_error, rate_error, rate_error])
        contractor = {"name": "Fail Co"}

        with patch("app.pipeline.research.asyncio.sleep", new_callable=AsyncMock):
            result = await research_contractor(client, contractor, contractor_id=3)

        assert result.success is False
        assert "Rate limited" in result.error

    async def test_no_retry_on_api_status_error(self):
        from openai import APIStatusError

        error_resp = MagicMock()
        error_resp.status_code = 401
        error_resp.headers = {}

        api_error = APIStatusError(
            message="Unauthorized",
            response=error_resp,
            body=None,
        )

        client = _make_mock_client(side_effect=api_error)
        contractor = {"name": "Auth Fail Co"}

        result = await research_contractor(client, contractor, contractor_id=4)

        assert result.success is False
        assert "401" in result.error
        # Should not retry — only 1 call
        assert client.chat.completions.create.call_count == 1

    async def test_unexpected_error(self):
        client = _make_mock_client(side_effect=ValueError("Something broke"))
        contractor = {"name": "Broken Co"}

        result = await research_contractor(client, contractor, contractor_id=5)

        assert result.success is False
        assert "Something broke" in result.error


@pytest.mark.asyncio
class TestResearchBatch:

    async def test_empty_batch(self):
        report = await research_batch([])
        assert isinstance(report, BatchResearchReport)
        assert report.total == 0
        assert report.results == []

    async def test_aggregates_results(self):
        with patch("app.pipeline.research._build_client") as mock_build:
            mock_build.return_value = _make_mock_client()
            with patch("app.pipeline.research.ENRICHMENT_DELAY_SECONDS", 0):
                contractors = [
                    {"id": 1, "name": "Co A"},
                    {"id": 2, "name": "Co B"},
                    {"id": 3, "name": "Co C"},
                ]
                report = await research_batch(contractors, concurrency=3)

        assert report.total == 3
        assert report.succeeded == 3
        assert report.failed == 0
        assert len(report.results) == 3

    async def test_calls_progress_callback(self):
        progress_calls = []

        def on_progress(result, completed, total):
            progress_calls.append((result.contractor_name, completed, total))

        with patch("app.pipeline.research._build_client") as mock_build:
            mock_build.return_value = _make_mock_client()
            with patch("app.pipeline.research.ENRICHMENT_DELAY_SECONDS", 0):
                contractors = [{"id": 1, "name": "Co A"}, {"id": 2, "name": "Co B"}]
                await research_batch(contractors, concurrency=2, on_progress=on_progress)

        assert len(progress_calls) == 2
        # Each call should report total=2
        for _, _, total in progress_calls:
            assert total == 2
