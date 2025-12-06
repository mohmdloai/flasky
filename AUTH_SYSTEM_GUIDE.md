# Authentication System & Unified Response Guide

This guide provides comprehensive documentation for the newly implemented authentication system and unified response pattern in your Flask application.

## Table of Contents

1. [Overview](#overview)
2. [Unified Response Pattern](#unified-response-pattern)
3. [Authentication System](#authentication-system)
4. [Pagination System](#pagination-system)
5. [Setup Instructions](#setup-instructions)
6. [API Endpoints](#api-endpoints)
7. [Usage Examples](#usage-examples)
8. [Security Best Practices](#security-best-practices)

---

## Overview

This Flask application now includes:

- ✅ **Unified Response Pattern**: Consistent API responses across all endpoints
- ✅ **JWT Authentication**: Token-based authentication with access and refresh tokens
- ✅ **Session Authentication**: Cookie-based session authentication
- ✅ **Hybrid Authentication**: Support for both JWT and session authentication
- ✅ **Role-Based Access Control (RBAC)**: Fine-grained permissions with roles
- ✅ **Email Verification**: Secure email verification flow
- ✅ **Password Reset**: Secure password reset via email
- ✅ **Pagination**: Page-based and limit/offset pagination for list endpoints

---

## Unified Response Pattern

All API responses follow a consistent format:

### Success Response
```json
{
  "success": true,
  "message": "Success message",
  "data": { /* response data */ },
  "meta": { /* optional metadata like pagination */ }
}
```

### Error Response
```json
{
  "success": false,
  "message": "Error message",
  "errors": { /* optional detailed errors */ },
  "error_code": "ERROR_CODE"
}
```

### Available Response Methods

- `UnifiedResponse.success(data, message, status_code, meta)` - 200
- `UnifiedResponse.created(data, message, resource_id)` - 201
- `UnifiedResponse.deleted(message)` - 200
- `UnifiedResponse.no_content()` - 204
- `UnifiedResponse.error(message, errors, status_code, error_code)` - 400
- `UnifiedResponse.validation_error(errors)` - 422
- `UnifiedResponse.unauthorized(message)` - 401
- `UnifiedResponse.forbidden(message)` - 403
- `UnifiedResponse.not_found(message)` - 404

---

## Authentication System

### Architecture

The authentication system uses a **hybrid approach**:

1. **JWT Tokens**: For API clients and mobile apps
   - Access tokens (15 min lifespan)
   - Refresh tokens (7 day lifespan)

2. **Session Cookies**: For web browsers
   - Server-side sessions (7 day lifespan)
   - Secure, HttpOnly cookies

### User Model

```python
User:
  - id, username, email, password_hash
  - first_name, last_name
  - email_verified, is_active
  - role (foreign key to Role)
  - created_at, updated_at, last_login
```

### Role Model (RBAC)

```python
Role:
  - id, name (admin, user, moderator)
  - description
  - permissions (JSON)
```

Default roles:
- **admin**: Full system access
- **user**: Basic user permissions
- **moderator**: Elevated permissions for content management

### Authentication Decorators

Use these decorators to protect your routes:

```python
from app.utils.decorators import (
    jwt_required,           # JWT only
    session_required,       # Session only
    auth_required,          # JWT or Session
    role_required,          # Check user role
    verified_required,      # Email verified only
    optional_auth           # Optional authentication
)

# Example usage
@bp.route('/profile')
@auth_required
def get_profile():
    user = g.current_user
    return UnifiedResponse.success(data=user.serialize())

@bp.route('/admin/users')
@auth_required
@role_required(['admin'])
def get_all_users():
    # Only admins can access
    pass
```

---

## Pagination System

### Page-Based Pagination

Request:
```
GET /api/products?page=2&page_size=10
```

Response:
```json
{
  "success": true,
  "message": "Products retrieved successfully",
  "data": [ /* products */ ],
  "meta": {
    "pagination": {
      "type": "page",
      "current_page": 2,
      "page_size": 10,
      "total_items": 100,
      "total_pages": 10,
      "has_next": true,
      "has_previous": true,
      "next_page": 3,
      "previous_page": 1
    }
  }
}
```

### Limit/Offset Pagination

Request:
```
GET /api/products?pagination_type=limit_offset&limit=10&offset=20
```

Response:
```json
{
  "success": true,
  "message": "Products retrieved successfully",
  "data": [ /* products */ ],
  "meta": {
    "pagination": {
      "type": "limit_offset",
      "limit": 10,
      "offset": 20,
      "total_items": 100,
      "returned_items": 10,
      "next_offset": 30,
      "previous_offset": 10,
      "has_next": true,
      "has_previous": true
    }
  }
}
```

---

## Setup Instructions

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Create a `.env` file in the project root:

```env
# Flask
SECRET_KEY=your-super-secret-key-change-in-production
FLASK_APP=app.py
FLASK_ENV=development

# JWT
JWT_SECRET_KEY=your-jwt-secret-key-change-in-production
JWT_ACCESS_TOKEN_EXPIRES=15  # minutes
JWT_REFRESH_TOKEN_EXPIRES=7  # days

# Session
SESSION_TYPE=filesystem  # or 'redis' for production
SESSION_COOKIE_SECURE=False  # Set to True in production with HTTPS
PERMANENT_SESSION_LIFETIME=7  # days

# Email
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
MAIL_DEFAULT_SENDER=your-email@gmail.com

# Frontend URL (for email links)
FRONTEND_URL=http://localhost:5173

# Celery
CELERY_BROKER_URL=amqp://admin:admin@localhost:5672//
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Redis (if using Redis for sessions)
REDIS_URL=redis://localhost:6379/1
```

### 3. Run Database Migration

```bash
python migrate_db.py
```

This will:
- Create all database tables
- Seed default roles (admin, user, moderator)
- Optionally create an admin user

### 4. Start the Application

```bash
python app.py
```

Or with Flask CLI:
```bash
flask run
```

---

## API Endpoints

### Authentication Endpoints

#### Register
```http
POST /api/auth/register
Content-Type: application/json

{
  "username": "john_doe",
  "email": "john@example.com",
  "password": "SecurePass123",
  "first_name": "John",
  "last_name": "Doe"
}
```

#### Login
```http
POST /api/auth/login
Content-Type: application/json

{
  "username": "john_doe",  # Can be username or email
  "password": "SecurePass123"
}

Response:
{
  "success": true,
  "message": "Login successful",
  "data": {
    "user": { /* user object */ },
    "access_token": "eyJ...",
    "refresh_token": "eyJ...",
    "token_type": "Bearer"
  }
}
```

#### Get Profile
```http
GET /api/auth/profile
Authorization: Bearer <access_token>
```

#### Update Profile
```http
PUT /api/auth/profile
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "first_name": "John",
  "last_name": "Doe",
  "email": "newemail@example.com"
}
```

#### Logout
```http
POST /api/auth/logout
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "refresh_token": "eyJ..."  # Optional
}
```

#### Refresh Token
```http
POST /api/auth/refresh
Content-Type: application/json

{
  "refresh_token": "eyJ..."
}
```

#### Verify Email
```http
POST /api/auth/verify-email
Content-Type: application/json

{
  "token": "verification_token_from_email"
}
```

#### Resend Verification Email
```http
POST /api/auth/resend-verification
Content-Type: application/json

{
  "email": "john@example.com"
}
```

#### Forgot Password
```http
POST /api/auth/forgot-password
Content-Type: application/json

{
  "email": "john@example.com"
}
```

#### Reset Password
```http
POST /api/auth/reset-password
Content-Type: application/json

{
  "token": "reset_token_from_email",
  "new_password": "NewSecurePass123"
}
```

#### Change Password
```http
POST /api/auth/change-password
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "current_password": "OldPass123",
  "new_password": "NewSecurePass123"
}
```

### Product Endpoints

#### List Products (with pagination)
```http
GET /api/products?page=1&page_size=10
GET /api/products?pagination_type=limit_offset&limit=10&offset=0
```

#### Create Product
```http
POST /api/products
Content-Type: application/json

{
  "name": "Product Name",
  "price": 29.99,
  "stock": 100
}
```

### Order Endpoints

#### List Orders (with pagination)
```http
GET /api/orders?page=1&page_size=10
Authorization: Bearer <access_token>  # Optional
```

#### Create Order
```http
POST /api/orders
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "name": "John Doe",
  "email": "john@example.com",
  "items": [
    {
      "product_id": 1,
      "quantity": 2
    }
  ]
}
```

#### Get Order
```http
GET /api/orders/1
```

#### Add Items to Order
```http
POST /api/orders/1/items
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "product_id": 2,
  "quantity": 1
}
```

#### Pay Order
```http
POST /api/orders/1/pay
Authorization: Bearer <access_token>
```

---

## Usage Examples

### Frontend (JavaScript/Fetch)

#### Register and Login
```javascript
// Register
const registerResponse = await fetch('http://localhost:5000/api/auth/register', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    username: 'john_doe',
    email: 'john@example.com',
    password: 'SecurePass123',
  }),
});

const registerData = await registerResponse.json();

// Login
const loginResponse = await fetch('http://localhost:5000/api/auth/login', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  credentials: 'include',  // Important for session cookies
  body: JSON.stringify({
    username: 'john_doe',
    password: 'SecurePass123',
  }),
});

const loginData = await loginResponse.json();
const accessToken = loginData.data.access_token;

// Store token in localStorage or memory
localStorage.setItem('access_token', accessToken);
```

#### Authenticated Requests
```javascript
const accessToken = localStorage.getItem('access_token');

const response = await fetch('http://localhost:5000/api/auth/profile', {
  method: 'GET',
  headers: {
    'Authorization': `Bearer ${accessToken}`,
    'Content-Type': 'application/json',
  },
  credentials: 'include',  // For session support
});

const data = await response.json();

if (!data.success) {
  // Handle error
  console.error(data.message);
}
```

#### Pagination
```javascript
const response = await fetch('http://localhost:5000/api/products?page=1&page_size=10');
const data = await response.json();

console.log(data.data);  // Products
console.log(data.meta.pagination);  // Pagination info
```

### Backend (Python)

#### Creating Protected Routes
```python
from flask import Blueprint, g
from app.utils.decorators import auth_required, role_required
from app.utils.response import UnifiedResponse

bp = Blueprint('custom', __name__, url_prefix='/api/custom')

@bp.route('/protected')
@auth_required
def protected_route():
    user = g.current_user
    return UnifiedResponse.success(
        data={'user_id': user.id},
        message='Access granted'
    )

@bp.route('/admin-only')
@auth_required
@role_required(['admin'])
def admin_route():
    return UnifiedResponse.success(
        message='Admin access granted'
    )
```

#### Using Pagination
```python
from app.utils.pagination import UnifiedPagination
from app.models import Product

@bp.route('/products')
def list_products():
    queryset = Product.query.order_by(Product.name)

    return UnifiedPagination.paginate_by_page(
        queryset=queryset,
        serializer_func=lambda p: p.serialize(),
        message="Products retrieved successfully"
    )
```

---

## Security Best Practices

### 1. Environment Variables

- **Never commit** `.env` files to version control
- Use strong, random values for `SECRET_KEY` and `JWT_SECRET_KEY`
- Generate keys with: `python -c "import secrets; print(secrets.token_hex(32))"`

### 2. HTTPS in Production

Update `.env` for production:
```env
SESSION_COOKIE_SECURE=True
SESSION_COOKIE_SAMESITE=Strict
```

### 3. CORS Configuration

Update CORS origins in `app/__init__.py` for production:
```python
CORS(app,
     origins=["https://yourdomain.com"],
     methods=["GET", "POST", "PUT", "DELETE"],
     allow_headers=["Content-Type", "Authorization"],
     supports_credentials=True)
```

### 4. Password Requirements

Current requirements (enforced by `validate_password_strength`):
- Minimum 8 characters
- At least one uppercase letter
- At least one lowercase letter
- At least one digit

### 5. Token Security

- Access tokens expire in 15 minutes (configurable)
- Refresh tokens expire in 7 days (configurable)
- Refresh tokens are stored in database and can be revoked
- Password changes revoke all refresh tokens

### 6. Email Verification

- Email verification links expire in 24 hours
- Password reset links expire in 1 hour
- Tokens are single-use only

### 7. Session Security

- Sessions use secure, HttpOnly cookies
- Sessions are signed to prevent tampering
- Use Redis for session storage in production

---

## Testing

### Manual Testing with cURL

```bash
# Register
curl -X POST http://localhost:5000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","email":"test@example.com","password":"TestPass123"}'

# Login
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"TestPass123"}'

# Get Profile (replace TOKEN with actual token)
curl -X GET http://localhost:5000/api/auth/profile \
  -H "Authorization: Bearer TOKEN"
```

### Automated Tests

Run existing tests:
```bash
pytest tests/
```

---

## Troubleshooting

### Common Issues

1. **"SECRET_KEY not set"**
   - Make sure `.env` file exists with `SECRET_KEY` defined

2. **"Invalid or expired token"**
   - Access token may have expired (15 min)
   - Use refresh token endpoint to get new access token

3. **"Email sending failed"**
   - Check email configuration in `.env`
   - For Gmail, use an App Password

4. **"Session not found"**
   - Clear browser cookies
   - Check `SESSION_TYPE` configuration

5. **CORS errors**
   - Verify frontend URL is in CORS origins list
   - Ensure `credentials: 'include'` is set in frontend requests

---

## Next Steps

1. **Add user_id to Order model** to associate orders with users
2. **Implement email queue** using Celery for async email sending
3. **Add rate limiting** to prevent abuse
4. **Implement audit logging** for security events
5. **Add two-factor authentication (2FA)** for enhanced security
6. **Create admin dashboard** for user management

---

## Support

For issues or questions, please refer to:
- Project documentation: `/docs.md`
- Strategy document: `/strategy.mmd`
- This guide: `/AUTH_SYSTEM_GUIDE.md`

---

**Built with ❤️ using Flask, SQLAlchemy, and JWT**
