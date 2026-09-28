import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.api.deps import get_current_active_user
from app.core.db import get_db
from app.models.user import User
from app.models.profile import UserProfile
from app.schemas.profile import UserProfileUpdate, UserProfileResponse

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("", response_model=UserProfileResponse)
async def get_profile(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Retrieve global user profile for the authenticated user, or initialize with defaults."""
    result = await db.execute(
        select(UserProfile).filter(UserProfile.user_id == current_user.id)
    )
    profile = result.scalars().first()

    if not profile:
        profile = UserProfile(
            user_id=current_user.id,
            preferred_role="AI/ML Engineer",
            target_difficulty="Intermediate",
            education="B.Tech Computer Science & AI",
            programming_languages=["Python", "Java", "SQL"],
            current_learning_topics=["LLMs", "RAG", "Transformers"],
            interview_goal="Senior AI/ML Engineer",
            stats={"interviews_completed": 0, "problems_solved": 0, "topics_completed": 0}
        )
        db.add(profile)
        await db.commit()
        await db.refresh(profile)

    return UserProfileResponse(
        preferred_role=profile.preferred_role,
        target_difficulty=profile.target_difficulty,
        education=profile.education,
        programming_languages=profile.programming_languages,
        current_learning_topics=profile.current_learning_topics,
        interview_goal=profile.interview_goal,
        stats=profile.stats,
        updated_at=profile.updated_at
    )


@router.put("", response_model=UserProfileResponse)
@router.patch("", response_model=UserProfileResponse)
async def update_profile(
    profile_in: UserProfileUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Update global user profile attributes (merging stats and updating goals)."""
    result = await db.execute(
        select(UserProfile).filter(UserProfile.user_id == current_user.id)
    )
    profile = result.scalars().first()

    if not profile:
        profile = UserProfile(user_id=current_user.id)
        db.add(profile)

    if profile_in.preferred_role is not None:
        profile.preferred_role = profile_in.preferred_role
    if profile_in.target_difficulty is not None:
        profile.target_difficulty = profile_in.target_difficulty
    if profile_in.education is not None:
        profile.education = profile_in.education
    if profile_in.programming_languages is not None:
        profile.programming_languages = profile_in.programming_languages
    if profile_in.current_learning_topics is not None:
        profile.current_learning_topics = profile_in.current_learning_topics
    if profile_in.interview_goal is not None:
        profile.interview_goal = profile_in.interview_goal
    if profile_in.stats is not None:
        merged_stats = dict(profile.stats or {})
        merged_stats.update(profile_in.stats)
        profile.stats = merged_stats

    await db.commit()
    await db.refresh(profile)

    return UserProfileResponse(
        preferred_role=profile.preferred_role,
        target_difficulty=profile.target_difficulty,
        education=profile.education,
        programming_languages=profile.programming_languages,
        current_learning_topics=profile.current_learning_topics,
        interview_goal=profile.interview_goal,
        stats=profile.stats,
        updated_at=profile.updated_at
    )


@router.get("/dashboard-stats")
async def get_dashboard_stats(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    from sqlalchemy import func
    from app.models.document import Document

    # Count uploaded documents
    doc_res = await db.execute(
        select(func.count(Document.id)).filter(Document.user_id == current_user.id)
    )
    documents_count = doc_res.scalar() or 0

    # Get User Profile Stats
    prof_res = await db.execute(
        select(UserProfile).filter(UserProfile.user_id == current_user.id)
    )
    profile = prof_res.scalars().first()
    stats = profile.stats or {} if profile else {}

    job_matches_count = stats.get("job_matches_count", 0)
    latest_score = stats.get("latest_match_score")
    readiness = f"{latest_score}%" if latest_score is not None else "85%"

    user_name = current_user.full_name or (current_user.email.split("@")[0].capitalize() if current_user.email else "User")

    return {
        "user_name": user_name,
        "job_matches_count": job_matches_count,
        "interview_readiness": readiness,
        "documents_count": documents_count,
        "latest_job_analysis": stats.get("latest_job_analysis")
    }

