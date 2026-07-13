from pydantic import BaseModel, Field
from typing import List, Optional

class SearchRequestSchema(BaseModel):
    departure_station: str = Field(..., title="Departure Station", description="The name of the departure station in English.", json_schema_extra={"examples": ["Osaka"]})
    arrival_station: str = Field(..., title="Arrival Station", description="The name of the arrival station in English.", json_schema_extra={"examples": ["Kyoto"]})
    departure_time: Optional[str] = Field(None, title="Departure Time", description="Optional departure time in HH:MM format.", json_schema_extra={"examples": ["10:00"]})
    departure_date: Optional[str] = Field(None, title="Departure Date", description="Optional departure date in YYYY-MM-DD format.", json_schema_extra={"examples": ["2024-10-01"]})

class StationSchema(BaseModel):
    name: str = Field(..., title="Station Name", description="The name of the station.", json_schema_extra={"examples": ["Osaka"]})
    lat: float = Field(..., title="Latitude", description="Latitude of the station.", json_schema_extra={"examples": [34.7024]})
    lng: float = Field(..., title="Longitude", description="Longitude of the station.", json_schema_extra={"examples": [135.4959]})
    platform: Optional[str] = Field(None, title="Platform", description="Platform number or name.", json_schema_extra={"examples": ["11"]})
    has_midori_office: bool = Field(False, title="Has Midori Office", description="True if the station has a JR ticket office (Midori no Madoguchi).", json_schema_extra={"examples": [True]})

class RouteSegmentSchema(BaseModel):
    segment_type: str = Field(..., title="Segment Type", description="Type of segment: train, bus, walk.")
    railway_name: str = Field(..., title="Railway Name", description="Name of the transport.")
    duration: str = Field("", title="Duration", description="Duration of this segment.")
    is_through: bool = Field(False, title="Is Through Service", description="True if no transfer is required.")

class RouteResponseSchema(BaseModel):
    id: str = Field(..., title="Route ID", description="Unique identifier for the route.", json_schema_extra={"examples": ["route_12345"]})
    departure_station: str = Field(..., title="Departure Station", description="The name of the departure station.", json_schema_extra={"examples": ["Osaka"]})
    arrival_station: str = Field(..., title="Arrival Station", description="The name of the arrival station.", json_schema_extra={"examples": ["Kyoto"]})
    railway_name: str = Field(..., title="Railway Name", description="The name of the railway company.", json_schema_extra={"examples": ["JR West"]})
    total_duration: str = Field(..., title="Total Duration", description="Total travel time formatted as string.", json_schema_extra={"examples": ["30m"]})
    total_fare: int = Field(..., title="Total Fare", description="Total fare in JPY.", json_schema_extra={"examples": [580]})
    transfer_count: int = Field(..., title="Transfer Count", description="Number of transfers required.", json_schema_extra={"examples": [0]})
    polyline: str = Field(..., title="Polyline", description="Google Maps encoded polyline string for the route path.", json_schema_extra={"examples": ["_p~iF~ps|U_ulLnnqC_mqNvxq`@"]})
    stations: List[StationSchema] = Field(..., title="Stations", description="List of stations along the route.")
    segments: List[RouteSegmentSchema] = Field([], title="Segments", description="List of segments along the route.")

class DepartureInfoSchema(BaseModel):
    time: str = Field(..., title="Departure Time", description="Departure time in HH:MM format.", json_schema_extra={"examples": ["10:00"]})
    train_name: str = Field(..., title="Train Name", description="Name of the train.", json_schema_extra={"examples": ["Special Rapid Service"]})

class TimetableResponseSchema(BaseModel):
    route_id: str = Field(..., title="Route ID", description="Unique identifier for the route.", json_schema_extra={"examples": ["route_12345"]})
    first_train: str = Field(..., title="First Train Time", description="First train time in HH:MM format.", json_schema_extra={"examples": ["05:00"]})
    last_train: str = Field(..., title="Last Train Time", description="Last train time in HH:MM format.", json_schema_extra={"examples": ["23:50"]})
    departures: List[DepartureInfoSchema] = Field(..., title="Departures", description="List of departures for this route.")

class MovementRequestSchema(BaseModel):
    route_id: str = Field(..., title="Route ID", description="Unique identifier of the selected route.", json_schema_extra={"examples": ["route_12345"]})
    selected_departure_time: str = Field(..., title="Selected Departure Time", description="User selected departure time.", json_schema_extra={"examples": ["10:00"]})
    selected_arrival_time: str = Field(..., title="Selected Arrival Time", description="User selected arrival time.", json_schema_extra={"examples": ["10:30"]})
    departure_station: str = Field(..., title="Departure Station", description="Departure station name.", json_schema_extra={"examples": ["Osaka"]})
    arrival_station: str = Field(..., title="Arrival Station", description="Arrival station name.", json_schema_extra={"examples": ["Kyoto"]})
    search_time: Optional[str] = Field(None, title="Search Time", description="Original search time.", json_schema_extra={"examples": ["10:00"]})
    search_date: Optional[str] = Field(None, title="Search Date", description="Original search date.", json_schema_extra={"examples": ["2024-10-01"]})

class MovementResponseSchema(BaseModel):
    route_id: str = Field(..., title="Route ID", description="Unique identifier of the selected route.", json_schema_extra={"examples": ["route_12345"]})
    departure_station: str = Field(..., title="Departure Station", description="Departure station name.", json_schema_extra={"examples": ["Osaka"]})
    arrival_station: str = Field(..., title="Arrival Station", description="Arrival station name.", json_schema_extra={"examples": ["Kyoto"]})
    selected_departure_time: str = Field(..., title="Selected Departure Time", description="User selected departure time.", json_schema_extra={"examples": ["10:00"]})
    selected_arrival_time: str = Field(..., title="Selected Arrival Time", description="User selected arrival time.", json_schema_extra={"examples": ["10:30"]})
    search_mode: str = Field(..., title="Search Mode", description="The search context mode.", json_schema_extra={"examples": ["ROUTE_WITH_TIME"]})
    status: str = Field("created", title="Status", description="The status of the movement saving process.", json_schema_extra={"examples": ["saved_to_notion"]})
    notion_url: str = Field(..., title="Notion URL", description="The URL of the created Notion page.", json_schema_extra={"examples": ["https://notion.so/my-workspace/movement-abc"]})

class StationSearchResponseSchema(BaseModel):
    id: str = Field(..., title="Station ID", description="Unique identifier for the station.", json_schema_extra={"examples": ["st_123"]})
    english_name: str = Field(..., title="English Name", description="The English name of the station.", json_schema_extra={"examples": ["Osaka"]})
    japanese_name: str = Field(..., title="Japanese Name", description="The Japanese name of the station.", json_schema_extra={"examples": ["大阪"]})
    has_midori_office: bool = Field(..., title="Has Midori Office", description="True if the station has a JR ticket office.", json_schema_extra={"examples": [True]})

ERROR_RESPONSES = {
    400: {
        "description": "Bad Request - Domain Validation Error",
        "content": {
            "application/json": {
                "example": {"detail": "Departure and arrival stations cannot be the same."}
            }
        }
    },
    404: {
        "description": "Not Found",
        "content": {
            "application/json": {
                "example": {"detail": "Requested resource not found."}
            }
        }
    },
    422: {
        "description": "Validation Error - Invalid parameters",
    },
    500: {
        "description": "Internal Server Error",
        "content": {
            "application/json": {
                "example": {"detail": "An unexpected server error occurred."}
            }
        }
    },
    502: {
        "description": "Bad Gateway - External Service Error (Scraper or Notion)",
        "content": {
            "application/json": {
                "example": {"detail": "Route search failed: Network timeout."}
            }
        }
    }
}
