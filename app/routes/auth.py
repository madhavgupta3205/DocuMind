"""
Authentication routes for user signup, login, and token management.
"""

from fastapi import APIRouter, HTTPException, status, Depends
from datetime import timedelta
from loguru import logger

from app.models.user import UserCreate, UserLogin, Token, UserResponse
from app.services.database import UserDB
from app.utils.auth import get_password_hash, verify_password, create_access_token
from app.config import settings
from app.middleware.auth_middleware import get_current_user
from app.models.user import TokenData

router = APIRouter(prefix="/api/v1/auth", tags=["authentication"])


@router.post("/signup", response_model=Token, status_code=status.HTTP_201_CREATED)
async def signup(user: UserCreate):
    """
    Register a new user account.

    Args:
        user: User registration data

    Returns:
        JWT access token

    Raises:
        HTTPException: If email already exists
    """
    existing_user = await UserDB.get_user_by_email(user.email)

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    hashed_password = get_password_hash(user.password)

    user_data = {
        "email": user.email,
        "hashed_password": hashed_password,
        "full_name": user.full_name
    }

    created_user = await UserDB.create_user(user_data)

    access_token_expires = timedelta(
        minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": created_user["email"], "user_id": created_user["_id"]},
        expires_delta=access_token_expires
    )

    logger.info(f"New user registered: {user.email}")

    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/login", response_model=Token)
async def login(user: UserLogin):
    """
    Authenticate user and return JWT token.

    Args:
        user: User login credentials

    Returns:
        JWT access token

    Raises:
        HTTPException: If credentials are invalid
    """
    db_user = await UserDB.get_user_by_email(user.email)

    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )

    if not verify_password(user.password, db_user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )

    access_token_expires = timedelta(
        minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": db_user["email"], "user_id": db_user["_id"]},
        expires_delta=access_token_expires
    )

    logger.info(f"User logged in: {user.email}")

    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: TokenData = Depends(get_current_user)):
    """
    Get current authenticated user information.

    Args:
        current_user: Current authenticated user from JWT token

    Returns:
        User information

    Raises:
        HTTPException: If user not found
    """
    db_user = await UserDB.get_user_by_id(current_user.user_id)

    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return {
        "id": db_user["_id"],
        "email": db_user["email"],
        "full_name": db_user.get("full_name"),
        "created_at": db_user["created_at"],
        "is_active": db_user["is_active"]
    }
