from fastapi import APIRouter, Depends

from backend.content.app.db_conn import get_db
from backend.content.schemas.users import UserProfileCreate
from backend.content.controller.AuthController import AuthController


router = APIRouter(prefix="/v1/auth", tags=["content"])


@router.post("/register")
async def register_user(response: Response, _db = Depends(get_db), user: UserProfileCreate = None):
    # call some funtion for business logic to register user in database
    _status, _data = await AuthController(_db).register_user(user)

    response.status_code = _status
    return _data