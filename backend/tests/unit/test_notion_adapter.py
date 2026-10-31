import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from domain.movement import Movement
from domain.route import Route
from domain.search import SearchContext, SearchMode
from infrastructure.notion.notion_mapper import NotionMapper
from infrastructure.notion.notion_client import NotionClient, NotionClientException
from infrastructure.notion.notion_adapter import RealNotionAdapter
from infrastructure.notion.constants import NotionColumns
from application.ports.notion_port import NotionException
from api.schemas import LegSelection

@pytest.fixture
def mock_movement():
    route = Route(
        id="route_1",
        departure_station="Shin-Osaka",
        arrival_station="Hagi",
        railway_name="Mixed",
        total_duration="4h",
        total_fare=12000,
        transfer_count=1,
        polyline="",
        stations=[]
    )
    context = SearchContext(
        departure_station="Shin-Osaka",
        arrival_station="Hagi",
        search_mode=SearchMode.ROUTE_ONLY,
        departure_time="08:00",
        departure_date="2026-08-10"
    )
    return Movement(
        route=route,
        selected_departure_time="08:00",
        selected_arrival_time="12:30",
        search_context=context
    )

def test_notion_mapper_parent_payload(mock_movement):
    """TEST 1: Parent payload matches column structures."""
    properties = NotionMapper.map_parent_movement(mock_movement)
    
    assert NotionColumns.ROUTE in properties
    assert properties[NotionColumns.ROUTE]["title"][0]["text"]["content"] == "Shin-Osaka -> Hagi"
    assert properties[NotionColumns.TRANSPORT_TYPE]["select"]["name"] == "Mixed"
    assert properties[NotionColumns.FARE]["number"] == 12000

@pytest.mark.asyncio
async def test_notion_adapter_parent_page_id(mock_movement):
    """TEST 2 & 7: Parent Page is created, ID is extracted, single save handles legs=None."""
    adapter = RealNotionAdapter()
    adapter.database_id = "default_db"
    
    adapter.client.get_child_database_id = AsyncMock(return_value="child_db_id")
    adapter.client.post_page = AsyncMock(return_value={"url": "http://success", "id": "parent-page-123"})
    
    result = await adapter.save_movement(mock_movement, target_page_id="test_page")
    
    assert result["notion_url"] == "http://success"
    assert result["parent_page_id"] == "parent-page-123"
    assert result["child_page_ids"] == []
    adapter.client.post_page.assert_called_once()

def test_notion_mapper_child_payload():
    """TEST 3: Child payload includes Parent item relation."""
    leg = LegSelection(
        segment_index=0,
        departure_station="A",
        arrival_station="B",
        departure_time="10:00",
        transport_name="Train",
        platform=2,
        base_fare=None,
        express_fare=None
    )
    
    properties = NotionMapper.map_leg(leg, "parent-page-id", "Parent item")
    
    assert "Parent item" in properties
    assert properties["Parent item"]["relation"][0]["id"] == "parent-page-id"
    assert properties[NotionColumns.ROUTE]["title"][0]["text"]["content"] == "A -> B"

@pytest.mark.parametrize(
    ("railway_name", "transport_name", "expected_transport_type"),
    [
        ("OsakaMetro Midosuji Line", "Local", "OsakaMetro Midosuji Line"),
        ("Tokyo Metro Ginza Line", "Local", "Tokyo Metro Ginza Line"),
        ("Kyoto Subway Karasuma Line", "Local", "Kyoto Subway Karasuma Line"),
        ("Toei Asakusa Line", "Local", "Toei Asakusa Line"),
        ("Toei Bus", "Bus", "Bus"),
        ("JR Kyoto Line", "Local", "Local"),
        ("JR Shinkansen Nozomi", "Shinkansen Nozomi", "Shinkansen Nozomi"),
        ("JR Kyoto Line", "Limited Express Thunderbird", "Limited Express Thunderbird"),
    ],
)
def test_notion_mapper_classifies_subway_transport(
    railway_name,
    transport_name,
    expected_transport_type,
):
    leg = LegSelection(
        segment_index=0,
        departure_station="A",
        arrival_station="B",
        departure_time="10:00",
        transport_name=transport_name,
        railway_name=railway_name,
    )

    properties = NotionMapper.map_leg(leg, "parent-page-id", "Parent item")

    assert properties[NotionColumns.TRANSPORT_TYPE]["select"]["name"] == expected_transport_type

@pytest.mark.asyncio
async def test_notion_adapter_multiple_legs(mock_movement):
    """TEST 4: Child creation results in exactly 1+N POST calls."""
    adapter = RealNotionAdapter()
    adapter.database_id = "default_db"
    
    adapter.client.get_child_database_id = AsyncMock(return_value="child_db_id")
    adapter.client.get_parent_item_property = AsyncMock(return_value="Parent item")
    
    # Mock post_page to return different IDs for parent and children
    mock_post_page = AsyncMock(side_effect=[
        {"url": "http://parent", "id": "parent-id"},
        {"url": "http://child1", "id": "child-1-id"},
        {"url": "http://child2", "id": "child-2-id"},
    ])
    adapter.client.post_page = mock_post_page
    
    legs = [
        LegSelection(segment_index=0, departure_station="A", arrival_station="B", departure_time="10:00"),
        LegSelection(segment_index=1, departure_station="B", arrival_station="C", departure_time="11:00")
    ]
    
    result = await adapter.save_movement(mock_movement, target_page_id="test_page", legs=legs)
    
    assert mock_post_page.call_count == 3
    assert result["parent_page_id"] == "parent-id"
    assert len(result["child_page_ids"]) == 2
    assert "child-1-id" in result["child_page_ids"]
    assert "child-2-id" in result["child_page_ids"]

@pytest.mark.asyncio
async def test_notion_adapter_child_failure_logs_and_raises(mock_movement):
    """TEST 5: Failure during child creation raises exception after parent is created."""
    adapter = RealNotionAdapter()
    adapter.database_id = "default_db"
    
    adapter.client.get_child_database_id = AsyncMock(return_value="child_db_id")
    adapter.client.get_parent_item_property = AsyncMock(return_value="Parent item")
    
    # Parent succeeds, child fails
    mock_post_page = AsyncMock(side_effect=[
        {"url": "http://parent", "id": "parent-id"},
        NotionClientException("API Error")
    ])
    adapter.client.post_page = mock_post_page
    
    legs = [LegSelection(segment_index=0, departure_station="A", arrival_station="B", departure_time="10:00")]
    
    with pytest.raises(NotionException, match="Failed to create child leg"):
        await adapter.save_movement(mock_movement, target_page_id="test_page", legs=legs)

@pytest.mark.asyncio
async def test_notion_adapter_backward_compatibility(mock_movement):
    """TEST 6: target_page_id=None -> default database."""
    adapter = RealNotionAdapter()
    adapter.database_id = "default_db_id"
    adapter.client.post_page = AsyncMock(return_value={"url": "http://success", "id": "old_page_id"})
    
    # Save without target_page_id
    result = await adapter.save_movement(mock_movement)
    
    assert result["notion_url"] == "http://success"
    # Ensure post_page was called with default_db_id
    adapter.client.post_page.assert_called_once()
    args, kwargs = adapter.client.post_page.call_args
    assert kwargs["database_id"] == "default_db_id"

@pytest.mark.asyncio
async def test_notion_client_pagination():
    """TEST 8: Page ID -> Transportation DB pagination test."""
    client = NotionClient(retries=1)
    
    mock_response_1 = MagicMock()
    mock_response_1.status_code = 200
    mock_response_1.json.return_value = {
        "results": [{"type": "paragraph"}],
        "has_more": True,
        "next_cursor": "cursor2"
    }
    
    mock_response_2 = MagicMock()
    mock_response_2.status_code = 200
    mock_response_2.json.return_value = {
        "results": [
            {
                "type": "child_database",
                "id": "db_id_on_page2",
                "child_database": {"title": "Transportation"}
            }
        ],
        "has_more": False
    }
    
    async def mock_get(url, params=None):
        if params and params.get("start_cursor") == "cursor2":
            return mock_response_2
        return mock_response_1
        
    with patch("httpx.AsyncClient.get", side_effect=mock_get):
        db_id = await client.get_child_database_id("test_page_id", "Transportation")
        assert db_id == "db_id_on_page2"
