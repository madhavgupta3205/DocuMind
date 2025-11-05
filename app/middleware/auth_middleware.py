"""
Authentication middleware for protecting routes with JWT verification.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional

from app.utils.auth import verify_token
from app.models.user import TokenData

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> TokenData:
    """
    Dependency to get the current authenticated user from JWT token.

    Args:
        credentials: HTTP Bearer token credentials

    Returns:
        TokenData object containing user information

    Raises:
        HTTPException: If authentication fails
    """
    token = credentials.credentials
    return verify_token(token)


async def get_current_active_user(
    current_user: TokenData = Depends(get_current_user)
) -> TokenData:
    """
    Dependency to ensure the current user is active.

    Args:
        current_user: The current authenticated user

    Returns:
        TokenData object if user is active

    Raises:
        HTTPException: If user is inactive
    """
    # In future, you can check user status from database
    return current_user
