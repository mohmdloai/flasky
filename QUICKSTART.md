# Quick Start Guide - Authentication System

## Installation & Setup (5 minutes)

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Create Environment File

Create a `.env` file in the project root with these essential variables:

```env
SECRET_KEY=change-this-to-a-random-string
JWT_SECRET_KEY=change-this-to-another-random-string
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
MAIL_DEFAULT_SENDER=your-email@gmail.com
```

Generate secure keys:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### 3. Run Database Migration
```bash
python migrate_db.py
```

Follow the prompts to create an admin user (optional).

### 4. Start the Application
```bash
python app.py
```

The API will be available at `http://localhost:5000`

---

## Test the System

### 1. Register a User
```bash
curl -X POST http://localhost:5000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "email": "test@example.com",
    "password": "TestPass123"
  }'
```

### 2. Login
```bash
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "password": "TestPass123"
  }'
```

Save the `access_token` from the response.

### 3. Access Protected Route
```bash
curl -X GET http://localhost:5000/api/auth/profile \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### 4. Test Pagination
```bash
curl http://localhost:5000/api/products?page=1&page_size=10
```

---

## Key Features

✅ **Unified Response Pattern** - All endpoints return consistent JSON format
✅ **JWT Authentication** - Token-based auth with access & refresh tokens
✅ **Session Authentication** - Cookie-based sessions for web browsers
✅ **Hybrid Auth** - Supports both JWT and sessions simultaneously
✅ **Email Verification** - Secure email verification workflow
✅ **Password Reset** - Email-based password reset
✅ **Role-Based Access Control** - Admin, User, Moderator roles
✅ **Pagination** - Page-based and limit/offset pagination

---

## Available Endpoints

### Authentication
- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login (returns JWT + session)
- `POST /api/auth/logout` - Logout
- `POST /api/auth/refresh` - Refresh access token
- `GET /api/auth/profile` - Get user profile (protected)
- `PUT /api/auth/profile` - Update profile (protected)
- `POST /api/auth/verify-email` - Verify email
- `POST /api/auth/resend-verification` - Resend verification
- `POST /api/auth/forgot-password` - Request password reset
- `POST /api/auth/reset-password` - Reset password
- `POST /api/auth/change-password` - Change password (protected)

### Products
- `GET /api/products` - List products (with pagination)
- `POST /api/products` - Create product

### Orders
- `GET /api/orders` - List orders (with pagination, optional auth)
- `POST /api/orders` - Create order (protected)
- `GET /api/orders/:id` - Get order details
- `POST /api/orders/:id/items` - Add items to order (protected)
- `POST /api/orders/:id/pay` - Pay for order (protected)

---

## Response Format

All responses follow this format:

**Success:**
```json
{
  "success": true,
  "message": "Operation successful",
  "data": { /* your data */ },
  "meta": { /* pagination, etc */ }
}
```

**Error:**
```json
{
  "success": false,
  "message": "Error description",
  "errors": { /* detailed errors */ },
  "error_code": "ERROR_CODE"
}
```

---

## Authentication Methods

### Method 1: JWT (Recommended for APIs)
```javascript
fetch('http://localhost:5000/api/auth/profile', {
  headers: {
    'Authorization': 'Bearer ' + accessToken
  }
})
```

### Method 2: Session Cookies (For Web Apps)
```javascript
fetch('http://localhost:5000/api/auth/profile', {
  credentials: 'include'  // Sends cookies
})
```

### Method 3: Hybrid (Both)
Both methods work simultaneously - the system checks JWT first, then session.

---

## Security Notes

1. **Change default keys** in `.env` before deploying
2. **Enable HTTPS** in production (set `SESSION_COOKIE_SECURE=True`)
3. **Configure CORS** for your frontend domain
4. **Use strong passwords** (min 8 chars, uppercase, lowercase, digit)
5. **Email verification** required for certain features

---

## Troubleshooting

**"SECRET_KEY not set"**
→ Create `.env` file with `SECRET_KEY` and `JWT_SECRET_KEY`

**"Email sending failed"**
→ Check email credentials in `.env`
→ For Gmail, use an App Password (not regular password)

**"Invalid token"**
→ Token expired (15 min for access tokens)
→ Use `/api/auth/refresh` endpoint

**Import errors**
→ Run `pip install -r requirements.txt`

---

## Next Steps

1. Read the full guide: `AUTH_SYSTEM_GUIDE.md`
2. Explore the codebase:
   - `app/utils/response.py` - Unified responses
   - `app/utils/pagination.py` - Pagination helpers
   - `app/auth_routes.py` - Auth endpoints
   - `app/utils/decorators.py` - Auth decorators
3. Customize email templates in `app/utils/email_service.py`
4. Add your own protected routes using the decorators

---

## Support

- Full documentation: `AUTH_SYSTEM_GUIDE.md`
- Migration guide: Run `python migrate_db.py`
- Test your setup with the examples above

Happy coding! 🚀
