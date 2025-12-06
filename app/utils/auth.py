"""
Authentication utilities for JWT, password hashing, and token generation.
"""
import jwt
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from flask import current_app
from werkzeug.security import generate_password_hash, check_password_hash


# ============= JWT Functions =============

def generate_access_token(user_id: int, username: str, role: str) -> str:
    """
    Generate a short-lived JWT access token (15 minutes).

    Args:
        user_id: User's ID
        username: User's username
        role: User's role name

    Returns:
        JWT access token string
    """
    expires_delta = timedelta(minutes=current_app.config.get('JWT_ACCESS_TOKEN_EXPIRES', 15))
    expires_at = datetime.utcnow() + expires_delta

    payload = {
        'user_id': user_id,
        'username': username,
        'role': role,
        'type': 'access',
        'exp': expires_at,
        'iat': datetime.utcnow()
    }

    token = jwt.encode(
        payload,
        current_app.config['JWT_SECRET_KEY'],
        algorithm='HS256'
    )

    return token


def generate_refresh_token_string(user_id: int) -> str:
    """
    Generate a long-lived JWT refresh token (7 days).
    This is just the JWT string - you still need to store it in the database.

    Args:
        user_id: User's ID

    Returns:
        JWT refresh token string
    """
    expires_delta = timedelta(days=current_app.config.get('JWT_REFRESH_TOKEN_EXPIRES', 7))
    expires_at = datetime.utcnow() + expires_delta

    payload = {
        'user_id': user_id,
        'type': 'refresh',
        'exp': expires_at,
        'iat': datetime.utcnow(),
        'jti': secrets.token_urlsafe(32)  # Unique token ID
    }

    token = jwt.encode(
        payload,
        current_app.config['JWT_SECRET_KEY'],
        algorithm='HS256'
    )

    return token


def decode_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Decode and verify a JWT token.

    Args:
        token: JWT token string

    Returns:
        Decoded payload dictionary or None if invalid
    """
    try:
        payload = jwt.decode(
            token,
            current_app.config['JWT_SECRET_KEY'],
            algorithms=['HS256']
        )
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def verify_token(token: str, token_type: str = 'access') -> Optional[Dict[str, Any]]:
    """
    Verify a JWT token and check its type.

    Args:
        token: JWT token string
        token_type: Expected token type ('access' or 'refresh')

    Returns:
        Decoded payload if valid, None otherwise
    """
    payload = decode_token(token)

    if not payload:
        return None

    # Verify token type
    if payload.get('type') != token_type:
        return None

    return payload


# ============= Password Utilities =============

def hash_password(password: str) -> str:
    """
    Hash a password using werkzeug's security functions.

    Args:
        password: Plain text password

    Returns:
        Hashed password
    """
    return generate_password_hash(password, method='pbkdf2:sha256')


def verify_password(password_hash: str, password: str) -> bool:
    """
    Verify a password against its hash.

    Args:
        password_hash: Hashed password
        password: Plain text password to verify

    Returns:
        True if password matches, False otherwise
    """
    return check_password_hash(password_hash, password)


# ============= Token Generation Utilities =============

def generate_secure_token(length: int = 32) -> str:
    """
    Generate a cryptographically secure random token.
    Used for email verification and password reset tokens.

    Args:
        length: Length of the token (default 32 bytes)

    Returns:
        URL-safe token string
    """
    return secrets.token_urlsafe(length)


def generate_email_verification_token() -> str:
    """
    Generate a token for email verification.

    Returns:
        URL-safe token string
    """
    return generate_secure_token(32)


def generate_password_reset_token() -> str:
    """
    Generate a token for password reset.

    Returns:
        URL-safe token string
    """
    return generate_secure_token(32)


# ============= Token Expiry Helpers =============

def get_email_verification_expiry() -> datetime:
    """
    Get the expiry datetime for email verification tokens (24 hours from now).

    Returns:
        DateTime object for token expiry
    """
    hours = current_app.config.get('EMAIL_VERIFICATION_EXPIRES', 24)
    return datetime.utcnow() + timedelta(hours=hours)


def get_password_reset_expiry() -> datetime:
    """
    Get the expiry datetime for password reset tokens (1 hour from now).

    Returns:
        DateTime object for token expiry
    """
    hours = current_app.config.get('PASSWORD_RESET_EXPIRES', 1)
    return datetime.utcnow() + timedelta(hours=hours)


def get_refresh_token_expiry() -> datetime:
    """
    Get the expiry datetime for refresh tokens (7 days from now).

    Returns:
        DateTime object for token expiry
    """
    days = current_app.config.get('JWT_REFRESH_TOKEN_EXPIRES', 7)
    return datetime.utcnow() + timedelta(days=days)


# ============= Password Validation =============

def validate_password_strength(password: str) -> tuple[bool, Optional[str]]:
    """
    Validate password strength.

    Requirements:
    - At least 8 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit

    Args:
        password: Password to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"

    if not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter"

    if not any(c.islower() for c in password):
        return False, "Password must contain at least one lowercase letter"

    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least one digit"

    return True, None


# ============= Email Validation =============

def validate_email(email: str) -> tuple[bool, Optional[str]]:
    """
    Basic email validation.

    Args:
        email: Email address to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not email or '@' not in email:
        return False, "Invalid email address"

    if len(email) < 5:
        return False, "Email address is too short"

    if len(email) > 120:
        return False, "Email address is too long"

    parts = email.split('@')
    if len(parts) != 2:
        return False, "Invalid email format"

    local, domain = parts
    if not local or not domain:
        return False, "Invalid email format"

    if '.' not in domain:
        return False, "Invalid email domain"

    return True, None


# ============= Username Validation =============

def validate_username(username: str) -> tuple[bool, Optional[str]]:
    """
    Validate username format.

    Requirements:
    - 3-80 characters
    - Alphanumeric and underscores only

    Args:
        username: Username to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not username:
        return False, "Username is required"

    if len(username) < 3:
        return False, "Username must be at least 3 characters long"

    if len(username) > 80:
        return False, "Username must be at most 80 characters long"

    if not username.replace('_', '').isalnum():
        return False, "Username can only contain letters, numbers, and underscores"

    return True, None
