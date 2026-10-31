"""Provider errors and debug logging must not disclose private payloads."""
import logging
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from infrastructure.notion.notion_client import NotionClient, NotionClientException
from infrastructure.notion.notion_mapper import NotionMapper
from domain.movement import Movement
from domain.search import SearchContext
from domain.enums import SearchMode
from tests.factories import journey


@pytest.mark.asyncio
@pytest.mark.parametrize('operation', ['post_page', 'get_child_database_id', 'get_database_schema'])
async def test_notion_error_body_is_not_exposed(operation, caplog):
    private_marker = 'private-upstream-payload-marker'
    client = NotionClient(retries=1)
    request = httpx.Request('POST' if operation == 'post_page' else 'GET', client.base_url)
    response = httpx.Response(403, text=private_marker, request=request)
    http = AsyncMock()
    http.post.return_value = response
    http.get.return_value = response
    with patch('infrastructure.notion.notion_client.httpx.AsyncClient') as factory:
        factory.return_value.__aenter__.return_value = http
        with caplog.at_level(logging.DEBUG, logger='autotrip'):
            with pytest.raises(NotionClientException) as error:
                if operation == 'post_page':
                    await client.post_page('11111111111111111111111111111111', {})
                else:
                    await getattr(client, operation)('11111111111111111111111111111111')
    assert private_marker not in str(error.value)
    assert private_marker not in caplog.text
    assert '403' in str(error.value)


def test_mapper_debug_log_contains_no_journey_values(caplog):
    private_marker = 'private-journey-station-marker'
    route = journey([private_marker, 'Destination'], ['Train'])
    movement = Movement(route=route, selected_departure_time='08:00', selected_arrival_time='09:00',
        search_context=SearchContext(departure_station=private_marker, arrival_station='Destination',
            search_mode=SearchMode.ROUTE_ONLY, departure_time=None, departure_date=None))
    with caplog.at_level(logging.DEBUG, logger='autotrip'):
        NotionMapper.map_parent_movement(movement)
    assert private_marker not in caplog.text
