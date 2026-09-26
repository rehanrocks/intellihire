from pydantic import BaseModel

class GetItemQuery(BaseModel):
    item_id: int
    # Add additional query parameters as needed