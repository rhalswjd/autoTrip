from pydantic import BaseModel, ConfigDict
from domain.route import Route
from domain.search import SearchContext

class Movement(BaseModel):
    """
    Represents the final, personalized journey chosen by the user.
    Combines the physical Route with the Search Context.
    This entity is passed to the NotionAdapter for saving.
    """
    model_config = ConfigDict(frozen=True)

    route: Route
    selected_departure_time: str
    selected_arrival_time: str
    search_context: SearchContext
