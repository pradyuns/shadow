from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.postgres import get_db
from app.models.beta_signup import BetaSignup
from app.schemas.public import BetaSignupAccepted, BetaSignupCreate

router = APIRouter(prefix="/public", tags=["public"])


@router.post("/beta-signups", response_model=BetaSignupAccepted, status_code=status.HTTP_202_ACCEPTED)
async def create_beta_signup(body: BetaSignupCreate, db: AsyncSession = Depends(get_db)) -> BetaSignupAccepted:
    email_normalized = body.email.strip().lower()
    result = await db.execute(select(BetaSignup.id).where(BetaSignup.email_normalized == email_normalized))
    existing = result.scalar_one_or_none()
    if existing:
        return BetaSignupAccepted()

    db.add(BetaSignup(email=body.email, email_normalized=email_normalized))
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()

    return BetaSignupAccepted()
