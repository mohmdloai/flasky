"""
Authentication decorators for protecting routes.
Supports both JWT and session-based authentication.
"""
from functools import wraps
from flask import request, session, g
from app.utils.auth import verify_token
from app.utils.response import UnifiedResponse
from app.models import User
from app import db
from typing import List, Optional


def get_token_from_header() -> Optional[str]:
    """
    Extract JWT token from Authorization header.

    Returns:
        Token string or None
    """
    auth_header = request.headers.get('Authorization', '')

    if auth_header.startswith('Bearer '):
        return auth_header[7:]  # Remove 'Bearer ' prefix

    return None


def jwt_required(f):
    """
    Decorator to protect routes with JWT authentication.
    Validates JWT token from Authorization header.
    Sets g.current_user to the authenticated user.

    Usage:
        @bp.route('/profile')
        @jwt_required
        def get_profile():
            user = g.current_user
            return UnifiedResponse.success(data=user.serialize())
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Get token from header
        token = get_token_from_header()

        if not token:
            return UnifiedResponse.unauthorized(
                message="Missing authentication token"
            )

        # Verify token
        payload = verify_token(token, token_type='access')

        if not payload:
            return UnifiedResponse.unauthorized(
                message="Invalid or expired token"
            )

        # Get user from database
        user_id = payload.get('user_id')
        user = db.session.get(User, user_id)

        if not user:
            return UnifiedResponse.unauthorized(
                message="User not found"
            )

        if not user.is_active:
            return UnifiedResponse.unauthorized(
                message="Account is deactivated"
            )

        # Set current user in Flask's g object
        g.current_user = user

        return f(*args, **kwargs)

    return decorated_function


def session_required(f):
    """
    Decorator to protect routes with session-based authentication.
    Validates session cookie.
    Sets g.current_user to the authenticated user.

    Usage:
        @bp.route('/profile')
        @session_required
        def get_profile():
            user = g.current_user
            return UnifiedResponse.success(data=user.serialize())
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check if user_id exists in session
        user_id = session.get('user_id')

        if not user_id:
            return UnifiedResponse.unauthorized(
                message="Not authenticated"
            )

        # Get user from database
        user = db.session.get(User, user_id)

        if not user:
            # Clear invalid session
            session.clear()
            return UnifiedResponse.unauthorized(
                message="User not found"
            )

        if not user.is_active:
            session.clear()
            return UnifiedResponse.unauthorized(
                message="Account is deactivated"
            )

        # Set current user in Flask's g object
        g.current_user = user

        return f(*args, **kwargs)

    return decorated_function


def auth_required(f):
    """
    Hybrid decorator that accepts both JWT and session authentication.
    Tries JWT first, then falls back to session.
    Sets g.current_user to the authenticated user.

    Usage:
        @bp.route('/profile')
        @auth_required
        def get_profile():
            user = g.current_user
            return UnifiedResponse.success(data=user.serialize())
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = None

        # Try JWT authentication first
        token = get_token_from_header()
        if token:
            payload = verify_token(token, token_type='access')
            if payload:
                user_id = payload.get('user_id')
                user = db.session.get(User, user_id)

        # If JWT failed, try session authentication
        if not user:
            user_id = session.get('user_id')
            if user_id:
                user = db.session.get(User, user_id)

        # If both methods failed
        if not user:
            return UnifiedResponse.unauthorized(
                message="Authentication required"
            )

        if not user.is_active:
            return UnifiedResponse.unauthorized(
                message="Account is deactivated"
            )

        # Set current user
        g.current_user = user

        return f(*args, **kwargs)

    return decorated_function


def role_required(allowed_roles: List[str]):
    """
    Decorator to check if user has required role.
    Must be used after @jwt_required, @session_required, or @auth_required.

    Args:
        allowed_roles: List of role names that are allowed

    Usage:
        @bp.route('/admin/users')
        @auth_required
        @role_required(['admin'])
        def get_all_users():
            # Only admins can access this
            pass
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Check if current_user is set
            if not hasattr(g, 'current_user') or not g.current_user:
                return UnifiedResponse.unauthorized(
                    message="Authentication required"
                )

            user = g.current_user

            # Check user role
            if not user.role or user.role.name not in allowed_roles:
                return UnifiedResponse.forbidden(
                    message=f"Insufficient permissions. Required roles: {', '.join(allowed_roles)}"
                )

            return f(*args, **kwargs)

        return decorated_function

    return decorator


def verified_required(f):
    """
    Decorator to ensure user has verified their email.
    Must be used after @jwt_required, @session_required, or @auth_required.

    Usage:
        @bp.route('/orders')
        @auth_required
        @verified_required
        def create_order():
            # Only verified users can create orders
            pass
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check if current_user is set
        if not hasattr(g, 'current_user') or not g.current_user:
            return UnifiedResponse.unauthorized(
                message="Authentication required"
            )

        user = g.current_user

        # Check email verification
        if not user.email_verified:
            return UnifiedResponse.forbidden(
                message="Email verification required. Please verify your email to access this resource."
            )

        return f(*args, **kwargs)

    return decorated_function


def optional_auth(f):
    """
    Decorator that optionally authenticates user but doesn't require it.
    If authenticated, sets g.current_user. Otherwise, g.current_user is None.
    Useful for routes that work for both authenticated and anonymous users.

    Usage:
        @bp.route('/products')
        @optional_auth
        def get_products():
            if hasattr(g, 'current_user') and g.current_user:
                # User is authenticated
                pass
            else:
                # User is anonymous
                pass
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = None

        # Try JWT authentication
        token = get_token_from_header()
        if token:
            payload = verify_token(token, token_type='access')
            if payload:
                user_id = payload.get('user_id')
                user = db.session.get(User, user_id)
                if user and user.is_active:
                    g.current_user = user

        # Try session authentication if JWT failed
        if not user:
            user_id = session.get('user_id')
            if user_id:
                user = db.session.get(User, user_id)
                if user and user.is_active:
                    g.current_user = user

        # If no authentication, set current_user to None
        if not user:
            g.current_user = None

        return f(*args, **kwargs)

    return decorated_function
