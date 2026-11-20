"""
FairMed Auth Service
Business logic for user registration, authentication, and JWT token issuance.
"""

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.user import User
from app.schemas.auth import UserRegisterRequest, UserLoginRequest, TokenResponse, UserProfileResponse
from app.security.password import hash_password, verify_password
from app.security.jwt_handler import create_access_token


class AuthService:
    @staticmethod
    def register(req: UserRegisterRequest, db: Session) -> TokenResponse:
        # Check if email is already taken
        existing_user = db.query(User).filter(User.email == req.email.lower()).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A user with this email address already exists."
            )

        hashed = hash_password(req.password)
        new_user = User(
            full_name=req.full_name.strip(),
            email=req.email.lower(),
            password_hash=hashed
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        # Generate JWT
        token = create_access_token({"sub": new_user.id, "email": new_user.email})
        return TokenResponse(
            access_token=token,
            token_type="bearer",
            user=UserProfileResponse.model_validate(new_user)
        )

    @staticmethod
    def login(req: UserLoginRequest, db: Session) -> TokenResponse:
        user = db.query(User).filter(User.email == req.email.lower()).first()
        if not user or not verify_password(req.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password."
            )

        token = create_access_token({"sub": user.id, "email": user.email})
        return TokenResponse(
            access_token=token,
            token_type="bearer",
            user=UserProfileResponse.model_validate(user)
        )
