from pydantic import BaseModel

class CreateItemCommand(BaseModel):
    item_name: str
    item_description: str
    # Add additional fields as needed for your domain