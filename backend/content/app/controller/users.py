"""Current-user endpoints: /users/me ... (US-1.4 dashboard identity, US-1.7 profile)."""
from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, require_roles
from app.core.permissions import Role
from app.database.models import User
from app.database.session import get_db
from app.schemas.user import ProfileResponse, ProfileUpdate, UserPublic
from app.services import profile_service

router = APIRouter(prefix="/users", tags=["Users"])

candidate_only = require_roles(Role.CANDIDATE)


@router.get("/me", response_model=UserPublic, summary="Who am I? (any logged-in role)")
def read_me(user: User = Depends(get_current_user)):
    return UserPublic.from_user(user)


@router.get("/me/profile", response_model=ProfileResponse, summary="US-1.7 Read my candidate profile")
def read_profile(user: User = Depends(candidate_only), db: Session = Depends(get_db)):
    profile = profile_service.get_or_create_profile(db, user)
    return profile_service.to_response(user, profile)


@router.put("/me/profile", response_model=ProfileResponse, summary="US-1.7 Update my candidate profile")
def update_profile(body: ProfileUpdate, user: User = Depends(candidate_only), db: Session = Depends(get_db)):
    profile = profile_service.update_profile(db, user, body)
    return profile_service.to_response(user, profile)


@router.post("/me/cv", response_model=ProfileResponse, summary="US-1.7 Upload or replace my CV (PDF, max 5 MB)")
def upload_cv(file: UploadFile = File(...), user: User = Depends(candidate_only), db: Session = Depends(get_db)):
    content = file.file.read()
    profile = profile_service.save_cv(db, user, file.filename or "", file.content_type, content)
    return profile_service.to_response(user, profile)


@router.get("/me/cv", summary="US-1.7 Download my CV")
def download_cv(user: User = Depends(candidate_only)):
    path = profile_service.cv_file_path(user)
    return FileResponse(path, media_type="application/pdf", filename=user.profile.cv_original_name or "cv.pdf")


@router.delete("/me/cv", response_model=ProfileResponse, summary="US-1.7 Remove my CV")
def delete_cv(user: User = Depends(candidate_only), db: Session = Depends(get_db)):
    profile = profile_service.delete_cv(db, user)
    return profile_service.to_response(user, profile)
