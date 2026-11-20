"""
FairMed Schemas - Authentication
Pydantic schemas for registration, login, token output, and user profile.
"""

from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, ConfigDict


class UserRegisterRequest(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=100, json_schema_extra={"example": "Aarav Sharma"})
    email: EmailStr = Field(..., json_schema_extra={"example": "patient@fairmed.org"})
    password: str = Field(..., min_length=6, max_length=128, json_schema_extra={"example": "SecurePassword123!"})


class UserLoginRequest(BaseModel):
    email: EmailStr = Field(..., json_schema_extra={"example": "patient@fairmed.org"})
    password: str = Field(..., json_schema_extra={"example": "SecurePassword123!"})


class UserProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    full_name: str
    email: str
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserProfileResponse
