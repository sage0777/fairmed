"""
FairMed Auth Router
Endpoints for user registration, login, and profile lookup.
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.auth import UserRegisterRequest, UserLoginRequest, TokenResponse, UserProfileResponse
from app.services.auth_service import AuthService
from app.security.dependencies import get_current_user

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register_user(req: UserRegisterRequest, db: Session = Depends(get_db)):
    """Registers a new user account and returns a JWT access token."""
    return AuthService.register(req, db)


@router.post("/login", response_model=TokenResponse)
def login_user(req: UserLoginRequest, db: Session = Depends(get_db)):
    """Authenticates user credentials and returns a JWT access token."""
    return AuthService.login(req, db)


@router.get("/profile", response_model=UserProfileResponse)
def get_user_profile(current_user: User = Depends(get_current_user)):
    """Retrieves profile information for the authenticated user."""
    return current_user
