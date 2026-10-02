"""Candidate profile rules (US-1.7)."""
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import FileTooLarge, InvalidFile, NotFound
from app.core.time import utcnow
from app.database.models import CandidateProfile, User
from app.schemas.user import CVInfo, EducationItem, ExperienceItem, ProfileResponse, ProfileUpdate
from app.services.storage import get_storage

# Which pieces make a profile "complete". Each is worth the same share.
COMPLETION_FIELDS = ["full_name", "job_title", "location", "bio", "skills", "education", "experience", "linkedin_url", "cv"]


def get_or_create_profile(db: Session, user: User) -> CandidateProfile:
    if user.profile is None:
        user.profile = CandidateProfile(user_id=user.id)
        db.commit()
        db.refresh(user)
    return user.profile


def completion(user: User, profile: CandidateProfile) -> tuple[int, list[str]]:
    present = {
        "full_name": bool(user.full_name),
        "job_title": bool(profile.job_title),
        "location": bool(profile.location),
        "bio": bool(profile.bio),
        "skills": bool(profile.skills),
        "education": bool(profile.education),
        "experience": bool(profile.experience),
        "linkedin_url": bool(profile.linkedin_url),
        "cv": bool(profile.cv_path),
    }
    missing = [name for name in COMPLETION_FIELDS if not present[name]]
    percent = round(100 * (len(COMPLETION_FIELDS) - len(missing)) / len(COMPLETION_FIELDS))
    return percent, missing


def to_response(user: User, profile: CandidateProfile) -> ProfileResponse:
    percent, missing = completion(user, profile)
    return ProfileResponse(
        user_id=user.id,
        full_name=user.full_name,
        email=user.email,
        job_title=profile.job_title,
        location=profile.location,
        linkedin_url=profile.linkedin_url,
        bio=profile.bio,
        education=[EducationItem(**e) for e in profile.education],
        experience=[ExperienceItem(**e) for e in profile.experience],
        skills=list(profile.skills),
        cv=CVInfo(original_name=profile.cv_original_name, uploaded_at=profile.cv_uploaded_at) if profile.cv_path else None,
        completion_percent=percent,
        missing_fields=missing,
    )


def update_profile(db: Session, user: User, data: ProfileUpdate) -> CandidateProfile:
    profile = get_or_create_profile(db, user)
    # exclude_unset: only touch fields the client actually sent (US-1.7: changes saved automatically).
    changes = data.model_dump(exclude_unset=True)
    if "full_name" in changes:
        user.full_name = changes.pop("full_name")
    for name, value in changes.items():
        if name in ("education", "experience") and value is not None:
            value = [item if isinstance(item, dict) else item.model_dump() for item in value]
        setattr(profile, name, value)
    db.commit()
    db.refresh(profile)
    return profile


def save_cv(db: Session, user: User, filename: str, content_type: str | None, content: bytes) -> CandidateProfile:
    settings = get_settings()
    if not filename or not filename.lower().endswith(".pdf"):
        raise InvalidFile("Only PDF files are accepted")
    if content_type not in (None, "", "application/pdf", "application/octet-stream"):
        raise InvalidFile("Only PDF files are accepted")
    if len(content) > settings.max_cv_size_bytes:
        raise FileTooLarge(f"CV must be {settings.max_cv_size_bytes // (1024 * 1024)} MB or smaller")
    # Trust the bytes, not the name: every real PDF starts with "%PDF-".
    if not content.startswith(b"%PDF-"):
        raise InvalidFile("The uploaded file is not a valid PDF")

    profile = get_or_create_profile(db, user)
    storage = get_storage()
    if profile.cv_path:
        storage.delete(profile.cv_path)
    profile.cv_path = storage.save(f"cvs/{user.id}", "pdf", content)
    profile.cv_original_name = filename[:255]
    profile.cv_uploaded_at = utcnow()
    db.commit()
    db.refresh(profile)
    return profile


def delete_cv(db: Session, user: User) -> CandidateProfile:
    profile = get_or_create_profile(db, user)
    if not profile.cv_path:
        raise NotFound("No CV uploaded")
    get_storage().delete(profile.cv_path)
    profile.cv_path = None
    profile.cv_original_name = None
    profile.cv_uploaded_at = None
    db.commit()
    db.refresh(profile)
    return profile


def cv_file_path(user: User) -> str:
    profile = user.profile
    if profile is None or not profile.cv_path:
        raise NotFound("No CV uploaded")
    path = get_storage().absolute_path(profile.cv_path)
    if not path.exists():
        raise NotFound("CV file is missing from storage")
    return str(path)
