from typing import Literal

from pydantic import BaseModel, EmailStr


class BetaSignupCreate(BaseModel):
    email: EmailStr


class BetaSignupAccepted(BaseModel):
    status: Literal["accepted"] = "accepted"
