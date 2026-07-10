from enum import Enum

class SearchMode(str, Enum):
    """
    Defines the workflow for route searching.
    Determined by the Application Service based on SearchRequest parameters.
    """
    ROUTE_ONLY = "ROUTE_ONLY"
    ROUTE_WITH_TIME = "ROUTE_WITH_TIME"
    ROUTE_WITH_DATETIME = "ROUTE_WITH_DATETIME"
