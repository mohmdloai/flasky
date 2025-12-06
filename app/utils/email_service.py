"""
Email service for sending authentication-related emails.
Uses Flask-Mail and Celery for asynchronous email delivery.
"""
from flask import current_app, render_template_string
from flask_mail import Message
from app import mail


# ============= Email Templates =============

VERIFICATION_EMAIL_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background-color: #4CAF50; color: white; padding: 20px; text-align: center; }
        .content { padding: 20px; background-color: #f9f9f9; }
        .button { display: inline-block; padding: 12px 24px; background-color: #4CAF50;
                  color: white; text-decoration: none; border-radius: 4px; margin: 20px 0; }
        .footer { padding: 20px; text-align: center; font-size: 12px; color: #666; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Email Verification</h1>
        </div>
        <div class="content">
            <h2>Hello {{ username }}!</h2>
            <p>Thank you for registering with us. Please verify your email address to activate your account.</p>
            <p>Click the button below to verify your email:</p>
            <a href="{{ verification_url }}" class="button">Verify Email</a>
            <p>Or copy and paste this link into your browser:</p>
            <p style="word-break: break-all;">{{ verification_url }}</p>
            <p><strong>This link will expire in 24 hours.</strong></p>
            <p>If you didn't create an account, please ignore this email.</p>
        </div>
        <div class="footer">
            <p>&copy; {{ year }} Your Company. All rights reserved.</p>
        </div>
    </div>
</body>
</html>
"""

PASSWORD_RESET_EMAIL_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background-color: #FF5722; color: white; padding: 20px; text-align: center; }
        .content { padding: 20px; background-color: #f9f9f9; }
        .button { display: inline-block; padding: 12px 24px; background-color: #FF5722;
                  color: white; text-decoration: none; border-radius: 4px; margin: 20px 0; }
        .footer { padding: 20px; text-align: center; font-size: 12px; color: #666; }
        .warning { background-color: #fff3cd; border-left: 4px solid #ffc107; padding: 10px; margin: 10px 0; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Password Reset</h1>
        </div>
        <div class="content">
            <h2>Hello {{ username }}!</h2>
            <p>We received a request to reset your password. Click the button below to create a new password:</p>
            <a href="{{ reset_url }}" class="button">Reset Password</a>
            <p>Or copy and paste this link into your browser:</p>
            <p style="word-break: break-all;">{{ reset_url }}</p>
            <p><strong>This link will expire in 1 hour.</strong></p>
            <div class="warning">
                <p><strong>Security Notice:</strong> If you didn't request a password reset, please ignore this email.
                Your password will remain unchanged.</p>
            </div>
        </div>
        <div class="footer">
            <p>&copy; {{ year }} Your Company. All rights reserved.</p>
        </div>
    </div>
</body>
</html>
"""

WELCOME_EMAIL_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background-color: #2196F3; color: white; padding: 20px; text-align: center; }
        .content { padding: 20px; background-color: #f9f9f9; }
        .button { display: inline-block; padding: 12px 24px; background-color: #2196F3;
                  color: white; text-decoration: none; border-radius: 4px; margin: 20px 0; }
        .footer { padding: 20px; text-align: center; font-size: 12px; color: #666; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Welcome!</h1>
        </div>
        <div class="content">
            <h2>Hello {{ username }}!</h2>
            <p>Welcome to our platform! Your account has been successfully verified.</p>
            <p>You can now enjoy all the features we have to offer:</p>
            <ul>
                <li>Browse our product catalog</li>
                <li>Place orders</li>
                <li>Track your shipments</li>
                <li>And much more!</li>
            </ul>
            <a href="{{ app_url }}" class="button">Get Started</a>
        </div>
        <div class="footer">
            <p>&copy; {{ year }} Your Company. All rights reserved.</p>
        </div>
    </div>
</body>
</html>
"""


# ============= Email Sending Functions =============

def send_email(to: str, subject: str, html_body: str):
    """
    Send an email using Flask-Mail.

    Args:
        to: Recipient email address
        subject: Email subject
        html_body: HTML email body
    """
    try:
        msg = Message(
            subject=subject,
            recipients=[to],
            html=html_body,
            sender=current_app.config.get('MAIL_DEFAULT_SENDER')
        )
        mail.send(msg)
        return True
    except Exception as e:
        current_app.logger.error(f"Failed to send email to {to}: {str(e)}")
        return False


def send_verification_email(user, token: str):
    """
    Send email verification link to user.

    Args:
        user: User model instance
        token: Verification token
    """
    from datetime import datetime

    # Build verification URL (adjust based on your frontend URL)
    frontend_url = current_app.config.get('FRONTEND_URL', 'http://localhost:5173')
    verification_url = f"{frontend_url}/verify-email?token={token}"

    html_body = render_template_string(
        VERIFICATION_EMAIL_TEMPLATE,
        username=user.username,
        verification_url=verification_url,
        year=datetime.now().year
    )

    subject = "Please verify your email address"

    return send_email(user.email, subject, html_body)


def send_password_reset_email(user, token: str):
    """
    Send password reset link to user.

    Args:
        user: User model instance
        token: Password reset token
    """
    from datetime import datetime

    # Build reset URL (adjust based on your frontend URL)
    frontend_url = current_app.config.get('FRONTEND_URL', 'http://localhost:5173')
    reset_url = f"{frontend_url}/reset-password?token={token}"

    html_body = render_template_string(
        PASSWORD_RESET_EMAIL_TEMPLATE,
        username=user.username,
        reset_url=reset_url,
        year=datetime.now().year
    )

    subject = "Password Reset Request"

    return send_email(user.email, subject, html_body)


def send_welcome_email(user):
    """
    Send welcome email to user after email verification.

    Args:
        user: User model instance
    """
    from datetime import datetime

    # Build app URL
    app_url = current_app.config.get('FRONTEND_URL', 'http://localhost:5173')

    html_body = render_template_string(
        WELCOME_EMAIL_TEMPLATE,
        username=user.username,
        app_url=app_url,
        year=datetime.now().year
    )

    subject = "Welcome to Our Platform!"

    return send_email(user.email, subject, html_body)


# ============= Celery Tasks (Optional - for async email sending) =============

def send_verification_email_async(user_id: int, token: str):
    """
    Send verification email asynchronously using Celery.

    Args:
        user_id: User's ID
        token: Verification token
    """
    from app.models import User
    from app import db

    user = db.session.get(User, user_id)
    if user:
        send_verification_email(user, token)


def send_password_reset_email_async(user_id: int, token: str):
    """
    Send password reset email asynchronously using Celery.

    Args:
        user_id: User's ID
        token: Password reset token
    """
    from app.models import User
    from app import db

    user = db.session.get(User, user_id)
    if user:
        send_password_reset_email(user, token)


def send_welcome_email_async(user_id: int):
    """
    Send welcome email asynchronously using Celery.

    Args:
        user_id: User's ID
    """
    from app.models import User
    from app import db

    user = db.session.get(User, user_id)
    if user:
        send_welcome_email(user)
