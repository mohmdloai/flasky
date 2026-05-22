"""
Authentication routes blueprint.
Handles user registration, login, logout, profile, email verification, and password reset.
"""
import io

from flask import Blueprint, current_app, request, session, g
from PIL import Image, UnidentifiedImageError

from app import db
from app.models import User, Role, RefreshToken, EmailVerificationToken, PasswordResetToken
from app.utils.response import UnifiedResponse
from app.utils.auth import (
    generate_access_token,
    generate_refresh_token_string,
    verify_token,
    generate_email_verification_token,
    generate_password_reset_token,
    get_email_verification_expiry,
    get_password_reset_expiry,
    get_refresh_token_expiry,
    validate_password_strength,
    validate_email,
    validate_username
)
from app.utils.decorators import auth_required, jwt_required, session_required
from app.utils.email_service import (
    send_verification_email,
    send_password_reset_email,
    send_welcome_email
)
from app.utils.storage import (
    upload_fileobj,
    delete_object,
    generate_object_key,
)
from datetime import datetime


ALLOWED_AVATAR_MIMES = {'image/jpeg', 'image/png', 'image/webp'}
MAX_AVATAR_BYTES = 5 * 1024 * 1024  # 5 MB
AVATAR_SIZE_PX = 512  # square; retina-friendly for a ~256px display
AVATAR_JPEG_QUALITY = 85


auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')


# ============= Registration & Login =============

@auth_bp.route('/register', methods=['POST'])
def register():
    """
    Register a new user.

    Request body:
        {
            "username": "string",
            "email": "string",
            "password": "string",
            "first_name": "string" (optional),
            "last_name": "string" (optional)
        }
    """
    if not request.is_json:
        return UnifiedResponse.error(
            message="Request must be JSON format",
            status_code=400
        )

    data = request.get_json()

    # Validate required fields
    required_fields = ['username', 'email', 'password']
    missing_fields = [field for field in required_fields if field not in data]

    if missing_fields:
        return UnifiedResponse.validation_error({
            'missing_fields': missing_fields
        })

    username = data['username']
    email = data['email'].lower().strip()
    password = data['password']

    # Validate username
    is_valid, error = validate_username(username)
    if not is_valid:
        return UnifiedResponse.validation_error({'username': error})

    # Validate email
    is_valid, error = validate_email(email)
    if not is_valid:
        return UnifiedResponse.validation_error({'email': error})

    # Validate password strength
    is_valid, error = validate_password_strength(password)
    if not is_valid:
        return UnifiedResponse.validation_error({'password': error})

    # Check if user already exists
    existing_user = User.query.filter(
        (User.username == username) | (User.email == email)
    ).first()

    if existing_user:
        if existing_user.username == username:
            return UnifiedResponse.error(
                message="Username already taken",
                error_code="USERNAME_EXISTS",
                status_code=409
            )
        else:
            return UnifiedResponse.error(
                message="Email already registered",
                error_code="EMAIL_EXISTS",
                status_code=409
            )

    try:
        # Get default 'user' role
        user_role = Role.query.filter_by(name='user').first()
        if not user_role:
            # Create default user role if it doesn't exist
            user_role = Role(name='user', description='Default user role')
            db.session.add(user_role)
            db.session.flush()

        # Create new user
        user = User(
            username=username,
            email=email,
            first_name=data.get('first_name'),
            last_name=data.get('last_name'),
            role_id=user_role.id
        )
        user.set_password(password)

        db.session.add(user)
        db.session.flush()

        # Create email verification token
        token_string = generate_email_verification_token()
        verification_token = EmailVerificationToken(
            user_id=user.id,
            token=token_string,
            expires_at=get_email_verification_expiry()
        )
        db.session.add(verification_token)
        db.session.commit()

        # Send verification email (synchronously for now, can be made async with Celery)
        send_verification_email(user, token_string)

        return UnifiedResponse.created(
            data=user.serialize(),
            message="Registration successful. Please check your email to verify your account.",
            resource_id=user.id
        )

    except Exception as e:
        db.session.rollback()
        return UnifiedResponse.error(
            message=f"Registration failed: {str(e)}",
            status_code=500
        )


@auth_bp.route('/login', methods=['POST'])
def login():
    """
    Login user with username/email and password.
    Returns access token, refresh token, and sets session cookie.

    Request body:
        {
            "username": "string",  // Can be username or email
            "password": "string"
        }
    """
    if not request.is_json:
        return UnifiedResponse.error(
            message="Request must be JSON format",
            status_code=400
        )

    data = request.get_json()

    # Validate required fields
    if not data.get('username') or not data.get('password'):
        return UnifiedResponse.validation_error({
            'message': 'Username and password are required'
        })

    username_or_email = data['username'].strip()
    password = data['password']

    # Find user by username or email
    user = User.query.filter(
        (User.username == username_or_email) | (User.email == username_or_email.lower())
    ).first()

    if not user or not user.check_password(password):
        return UnifiedResponse.error(
            message="Invalid credentials",
            error_code="INVALID_CREDENTIALS",
            status_code=401
        )

    if not user.is_active:
        return UnifiedResponse.error(
            message="Account is deactivated",
            error_code="ACCOUNT_DEACTIVATED",
            status_code=403
        )

    try:
        # Generate tokens
        access_token = generate_access_token(user.id, user.username, user.role.name)
        refresh_token_string = generate_refresh_token_string(user.id)

        # Store refresh token in database
        refresh_token = RefreshToken(
            user_id=user.id,
            token=refresh_token_string,
            expires_at=get_refresh_token_expiry()
        )
        db.session.add(refresh_token)

        # Update last login
        user.last_login = datetime.utcnow()

        db.session.commit()

        # Set session cookie (for hybrid auth)
        session['user_id'] = user.id
        session['username'] = user.username

        return UnifiedResponse.success(
            data={
                'user': user.serialize(),
                'access_token': access_token,
                'refresh_token': refresh_token_string,
                'token_type': 'Bearer'
            },
            message="Login successful"
        )

    except Exception as e:
        db.session.rollback()
        return UnifiedResponse.error(
            message=f"Login failed: {str(e)}",
            status_code=500
        )


@auth_bp.route('/logout', methods=['POST'])
@auth_required
def logout():
    """
    Logout user. Revokes refresh token and clears session.
    Optionally accepts refresh token in request body to revoke it.
    """
    user = g.current_user

    try:
        # Get refresh token from request body if provided
        if request.is_json:
            data = request.get_json()
            refresh_token_string = data.get('refresh_token')

            if refresh_token_string:
                # Revoke the specific refresh token
                refresh_token = RefreshToken.query.filter_by(
                    token=refresh_token_string,
                    user_id=user.id
                ).first()

                if refresh_token:
                    refresh_token.revoke()

        # Clear session
        session.clear()

        db.session.commit()

        return UnifiedResponse.success(
            message="Logout successful"
        )

    except Exception as e:
        db.session.rollback()
        return UnifiedResponse.error(
            message=f"Logout failed: {str(e)}",
            status_code=500
        )


@auth_bp.route('/refresh', methods=['POST'])
def refresh():
    """
    Exchange refresh token for new access token.

    Request body:
        {
            "refresh_token": "string"
        }
    """
    if not request.is_json:
        return UnifiedResponse.error(
            message="Request must be JSON format",
            status_code=400
        )

    data = request.get_json()
    refresh_token_string = data.get('refresh_token')

    if not refresh_token_string:
        return UnifiedResponse.validation_error({
            'refresh_token': 'Refresh token is required'
        })

    # Verify JWT token
    payload = verify_token(refresh_token_string, token_type='refresh')

    if not payload:
        return UnifiedResponse.error(
            message="Invalid or expired refresh token",
            error_code="INVALID_REFRESH_TOKEN",
            status_code=401
        )

    # Check if token exists in database and is valid
    refresh_token = RefreshToken.query.filter_by(
        token=refresh_token_string
    ).first()

    if not refresh_token or not refresh_token.is_valid():
        return UnifiedResponse.error(
            message="Refresh token is invalid or revoked",
            error_code="INVALID_REFRESH_TOKEN",
            status_code=401
        )

    # Get user
    user = db.session.get(User, refresh_token.user_id)

    if not user or not user.is_active:
        return UnifiedResponse.error(
            message="User not found or inactive",
            status_code=401
        )

    # Generate new access token
    access_token = generate_access_token(user.id, user.username, user.role.name)

    return UnifiedResponse.success(
        data={
            'access_token': access_token,
            'token_type': 'Bearer'
        },
        message="Token refreshed successfully"
    )


# ============= Profile Management =============

@auth_bp.route('/profile', methods=['GET'])
@auth_required
def get_profile():
    """Get current user's profile."""
    user = g.current_user

    return UnifiedResponse.success(
        data=user.serialize(),
        message="Profile retrieved successfully"
    )


@auth_bp.route('/profile', methods=['PUT'])
@auth_required
def update_profile():
    """
    Update current user's profile.

    Request body:
        {
            "first_name": "string" (optional),
            "last_name": "string" (optional),
            "email": "string" (optional)
        }
    """
    user = g.current_user

    if not request.is_json:
        return UnifiedResponse.error(
            message="Request must be JSON format",
            status_code=400
        )

    data = request.get_json()

    try:
        # Update first name
        if 'first_name' in data:
            user.first_name = data['first_name']

        # Update last name
        if 'last_name' in data:
            user.last_name = data['last_name']

        # Update email (requires re-verification)
        if 'email' in data:
            new_email = data['email'].lower().strip()

            # Validate email
            is_valid, error = validate_email(new_email)
            if not is_valid:
                return UnifiedResponse.validation_error({'email': error})

            # Check if email is already taken
            if new_email != user.email:
                existing_user = User.query.filter_by(email=new_email).first()
                if existing_user:
                    return UnifiedResponse.error(
                        message="Email already in use",
                        error_code="EMAIL_EXISTS",
                        status_code=409
                    )

                user.email = new_email
                user.email_verified = False

                # Create new verification token
                token_string = generate_email_verification_token()
                verification_token = EmailVerificationToken(
                    user_id=user.id,
                    token=token_string,
                    expires_at=get_email_verification_expiry()
                )
                db.session.add(verification_token)

                # Send verification email
                send_verification_email(user, token_string)

        db.session.commit()

        return UnifiedResponse.success(
            data=user.serialize(),
            message="Profile updated successfully"
        )

    except Exception as e:
        db.session.rollback()
        return UnifiedResponse.error(
            message=f"Profile update failed: {str(e)}",
            status_code=500
        )


# ============= Avatar =============

@auth_bp.route('/profile/avatar', methods=['POST'])
@auth_required
def upload_avatar():
    """
    Upload (or replace) the current user's avatar.

    Multipart upload: field name "file". Image is validated via Pillow
    (rejects anything that isn't a real JPEG/PNG/WebP), resized to a square
    AVATAR_SIZE_PX × AVATAR_SIZE_PX JPEG, then uploaded to the avatars bucket.
    The previous avatar object — if any — is deleted only after the new one
    is successfully recorded in the DB.
    """
    user = g.current_user
    file = request.files.get('file')
    if not file:
        return UnifiedResponse.validation_error({'file': 'file is required (multipart/form-data)'})

    if file.mimetype not in ALLOWED_AVATAR_MIMES:
        return UnifiedResponse.validation_error({
            'file': f"Unsupported type {file.mimetype}; allowed: {', '.join(sorted(ALLOWED_AVATAR_MIMES))}"
        })

    file.stream.seek(0, 2)
    size = file.stream.tell()
    file.stream.seek(0)
    if size > MAX_AVATAR_BYTES:
        return UnifiedResponse.validation_error({
            'file': f'File too large ({size} bytes); max {MAX_AVATAR_BYTES}'
        })

    # Pillow doubles as MIME validation — Image.open rejects anything that
    # isn't a real image regardless of the Content-Type header.
    try:
        img = Image.open(file.stream)
        img.load()
    except (UnidentifiedImageError, OSError):
        return UnifiedResponse.validation_error({'file': 'File is not a valid image'})

    # Flatten transparency onto white so JPEG output looks right.
    if img.mode in ('RGBA', 'LA', 'P'):
        background = Image.new('RGB', img.size, (255, 255, 255))
        rgba = img.convert('RGBA')
        background.paste(rgba, mask=rgba.split()[-1])
        img = background
    elif img.mode != 'RGB':
        img = img.convert('RGB')

    img.thumbnail((AVATAR_SIZE_PX, AVATAR_SIZE_PX), Image.LANCZOS)

    buf = io.BytesIO()
    img.save(buf, format='JPEG', quality=AVATAR_JPEG_QUALITY, optimize=True)
    buf.seek(0)

    bucket = current_app.config['MINIO_BUCKET_AVATARS']
    new_key = generate_object_key(f'user-{user.id}', 'avatar.jpg')

    try:
        upload_fileobj(bucket, new_key, buf, content_type='image/jpeg')
    except Exception as e:
        return UnifiedResponse.error(
            message=f'Upload to storage failed: {str(e)}',
            status_code=502,
        )

    old_bucket, old_key = user.avatar_bucket, user.avatar_object_key
    try:
        user.avatar_bucket = bucket
        user.avatar_object_key = new_key
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        delete_object(bucket, new_key)
        return UnifiedResponse.error(
            message=f'Failed to update avatar: {str(e)}',
            status_code=500,
        )

    # New key committed — safe to drop the old blob.
    if old_bucket and old_key:
        delete_object(old_bucket, old_key)

    return UnifiedResponse.success(
        data=user.serialize(),
        message='Avatar updated successfully',
    )


@auth_bp.route('/profile/avatar', methods=['DELETE'])
@auth_required
def delete_avatar():
    """Remove the current user's avatar (no-op if none set)."""
    user = g.current_user
    old_bucket, old_key = user.avatar_bucket, user.avatar_object_key
    if not old_bucket or not old_key:
        return UnifiedResponse.success(
            data=user.serialize(),
            message='No avatar to remove',
        )

    try:
        user.avatar_bucket = None
        user.avatar_object_key = None
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return UnifiedResponse.error(
            message=f'Failed to remove avatar: {str(e)}',
            status_code=500,
        )

    delete_object(old_bucket, old_key)

    return UnifiedResponse.success(
        data=user.serialize(),
        message='Avatar removed successfully',
    )


# ============= Email Verification =============

@auth_bp.route('/verify-email', methods=['POST'])
def verify_email():
    """
    Verify user email with token.

    Request body:
        {
            "token": "string"
        }
    """
    if not request.is_json:
        return UnifiedResponse.error(
            message="Request must be JSON format",
            status_code=400
        )

    data = request.get_json()
    token_string = data.get('token')

    if not token_string:
        return UnifiedResponse.validation_error({
            'token': 'Verification token is required'
        })

    # Find token in database
    verification_token = EmailVerificationToken.query.filter_by(
        token=token_string
    ).first()

    if not verification_token or not verification_token.is_valid():
        return UnifiedResponse.error(
            message="Invalid or expired verification token",
            error_code="INVALID_TOKEN",
            status_code=400
        )

    try:
        # Get user
        user = db.session.get(User, verification_token.user_id)

        if not user:
            return UnifiedResponse.error(
                message="User not found",
                status_code=404
            )

        # Mark email as verified
        user.email_verified = True
        verification_token.mark_used()

        db.session.commit()

        # Send welcome email
        send_welcome_email(user)

        return UnifiedResponse.success(
            data=user.serialize(),
            message="Email verified successfully"
        )

    except Exception as e:
        db.session.rollback()
        return UnifiedResponse.error(
            message=f"Email verification failed: {str(e)}",
            status_code=500
        )


@auth_bp.route('/resend-verification', methods=['POST'])
def resend_verification():
    """
    Resend email verification link.

    Request body:
        {
            "email": "string"
        }
    """
    if not request.is_json:
        return UnifiedResponse.error(
            message="Request must be JSON format",
            status_code=400
        )

    data = request.get_json()
    email = data.get('email', '').lower().strip()

    if not email:
        return UnifiedResponse.validation_error({
            'email': 'Email is required'
        })

    # Find user
    user = User.query.filter_by(email=email).first()

    if not user:
        # Don't reveal if email exists
        return UnifiedResponse.success(
            message="If the email exists, a verification link has been sent"
        )

    if user.email_verified:
        return UnifiedResponse.error(
            message="Email is already verified",
            status_code=400
        )

    try:
        # Create new verification token
        token_string = generate_email_verification_token()
        verification_token = EmailVerificationToken(
            user_id=user.id,
            token=token_string,
            expires_at=get_email_verification_expiry()
        )
        db.session.add(verification_token)
        db.session.commit()

        # Send verification email
        send_verification_email(user, token_string)

        return UnifiedResponse.success(
            message="Verification email sent successfully"
        )

    except Exception as e:
        db.session.rollback()
        return UnifiedResponse.error(
            message=f"Failed to send verification email: {str(e)}",
            status_code=500
        )


# ============= Password Reset =============

@auth_bp.route('/forgot-password', methods=['POST'])
def forgot_password():
    """
    Request password reset link.

    Request body:
        {
            "email": "string"
        }
    """
    if not request.is_json:
        return UnifiedResponse.error(
            message="Request must be JSON format",
            status_code=400
        )

    data = request.get_json()
    email = data.get('email', '').lower().strip()

    if not email:
        return UnifiedResponse.validation_error({
            'email': 'Email is required'
        })

    # Find user
    user = User.query.filter_by(email=email).first()

    if not user:
        # Don't reveal if email exists      
        return UnifiedResponse.success(
            message="If the email exists, a password reset link has been sent"
        )

    try:
        # Create password reset token
        token_string = generate_password_reset_token()
        reset_token = PasswordResetToken(
            user_id=user.id,
            token=token_string,
            expires_at=get_password_reset_expiry()
        )
        db.session.add(reset_token)
        db.session.commit()

        # Send password reset email
        send_password_reset_email(user, token_string)

        return UnifiedResponse.success(
            message="Password reset link sent successfully"
        )

    except Exception as e:
        db.session.rollback()
        return UnifiedResponse.error(
            message=f"Failed to send password reset email: {str(e)}",
            status_code=500
        )


@auth_bp.route('/reset-password', methods=['POST'])
def reset_password():
    """
    Reset password with token.

    Request body:
        {
            "token": "string",
            "new_password": "string"
        }
    """
    if not request.is_json:
        return UnifiedResponse.error(
            message="Request must be JSON format",
            status_code=400
        )

    data = request.get_json()
    token_string = data.get('token')
    new_password = data.get('new_password')

    if not token_string or not new_password:
        return UnifiedResponse.validation_error({
            'message': 'Token and new password are required'
        })

    # Validate password strength
    is_valid, error = validate_password_strength(new_password)
    if not is_valid:
        return UnifiedResponse.validation_error({'password': error})

    # Find token in database
    reset_token = PasswordResetToken.query.filter_by(
        token=token_string
    ).first()

    if not reset_token or not reset_token.is_valid():
        return UnifiedResponse.error(
            message="Invalid or expired reset token",
            error_code="INVALID_TOKEN",
            status_code=400
        )

    try:
        # Get user
        user = db.session.get(User, reset_token.user_id)

        if not user:
            return UnifiedResponse.error(
                message="User not found",
                status_code=404
            )

        # Update password
        user.set_password(new_password)
        reset_token.mark_used()

        # Revoke all refresh tokens for security
        RefreshToken.query.filter_by(user_id=user.id).update({'revoked': True})

        db.session.commit()

        return UnifiedResponse.success(
            message="Password reset successfully. Please login with your new password."
        )

    except Exception as e:
        db.session.rollback()
        return UnifiedResponse.error(
            message=f"Password reset failed: {str(e)}",
            status_code=500
        )


@auth_bp.route('/change-password', methods=['POST'])
@auth_required
def change_password():
    """
    Change password for authenticated user.

    Request body:
        {
            "current_password": "string",
            "new_password": "string"
        }
    """
    user = g.current_user

    if not request.is_json:
        return UnifiedResponse.error(
            message="Request must be JSON format",
            status_code=400
        )

    data = request.get_json()
    current_password = data.get('current_password')
    new_password = data.get('new_password')

    if not current_password or not new_password:
        return UnifiedResponse.validation_error({
            'message': 'Current password and new password are required'
        })

    # Verify current password
    if not user.check_password(current_password):
        return UnifiedResponse.error(
            message="Current password is incorrect",
            error_code="INVALID_PASSWORD",
            status_code=400
        )

    # Validate new password strength
    is_valid, error = validate_password_strength(new_password)
    if not is_valid:
        return UnifiedResponse.validation_error({'password': error})

    try:
        # Update password
        user.set_password(new_password)

        # Revoke all refresh tokens for security
        RefreshToken.query.filter_by(user_id=user.id).update({'revoked': True})

        db.session.commit()

        return UnifiedResponse.success(
            message="Password changed successfully. Please login again with your new password."
        )

    except Exception as e:
        db.session.rollback()
        return UnifiedResponse.error(
            message=f"Password change failed: {str(e)}",
            status_code=500
        )
