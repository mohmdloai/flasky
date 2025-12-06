#!/usr/bin/env python
"""
Database migration script for authentication system.

This script creates all necessary database tables for the authentication system,
including User, Role, RefreshToken, EmailVerificationToken, and PasswordResetToken.

It also seeds default roles (admin, user, moderator) if they don't exist.

Usage:
    python migrate_db.py
"""
from app import create_app, db
from app.models import Role, User, RefreshToken, EmailVerificationToken, PasswordResetToken


def create_tables():
    """Create all database tables."""
    print("Creating database tables...")
    db.create_all()
    print("✓ Database tables created successfully")


def seed_roles():
    """Seed default roles if they don't exist."""
    print("\nSeeding default roles...")

    roles_to_create = [
        {
            'name': 'admin',
            'description': 'Administrator with full permissions',
            'permissions': {
                'all': True,
                'manage_users': True,
                'manage_products': True,
                'manage_orders': True,
                'view_analytics': True
            }
        },
        {
            'name': 'user',
            'description': 'Regular user with basic permissions',
            'permissions': {
                'read': True,
                'create_order': True,
                'view_own_orders': True
            }
        },
        {
            'name': 'moderator',
            'description': 'Moderator with elevated permissions',
            'permissions': {
                'read': True,
                'create_order': True,
                'manage_products': True,
                'view_orders': True,
                'update_order_status': True
            }
        }
    ]

    created_count = 0
    for role_data in roles_to_create:
        existing_role = Role.query.filter_by(name=role_data['name']).first()

        if not existing_role:
            role = Role(
                name=role_data['name'],
                description=role_data['description'],
                permissions=role_data['permissions']
            )
            db.session.add(role)
            created_count += 1
            print(f"  ✓ Created role: {role_data['name']}")
        else:
            print(f"  - Role already exists: {role_data['name']}")

    if created_count > 0:
        db.session.commit()
        print(f"\n✓ Successfully created {created_count} role(s)")
    else:
        print("\n✓ All roles already exist")


def create_admin_user():
    """
    Create an admin user if one doesn't exist.
    This is optional and can be skipped.
    """
    print("\n" + "="*60)
    create_admin = input("Do you want to create an admin user? (y/n): ").strip().lower()

    if create_admin != 'y':
        print("Skipping admin user creation")
        return

    # Check if admin user already exists
    existing_admin = User.query.join(Role).filter(Role.name == 'admin').first()

    if existing_admin:
        print(f"✓ Admin user already exists: {existing_admin.username}")
        return

    print("\nEnter admin user details:")
    username = input("Username: ").strip()
    email = input("Email: ").strip().lower()
    password = input("Password: ").strip()

    if not username or not email or not password:
        print("✗ All fields are required. Skipping admin user creation.")
        return

    try:
        # Get admin role
        admin_role = Role.query.filter_by(name='admin').first()

        if not admin_role:
            print("✗ Admin role not found. Please run the migration first.")
            return

        # Create admin user
        admin_user = User(
            username=username,
            email=email,
            role_id=admin_role.id,
            email_verified=True,  # Auto-verify admin
            is_active=True
        )
        admin_user.set_password(password)

        db.session.add(admin_user)
        db.session.commit()

        print(f"\n✓ Admin user created successfully!")
        print(f"  Username: {username}")
        print(f"  Email: {email}")
        print(f"  Role: admin")

    except Exception as e:
        db.session.rollback()
        print(f"\n✗ Failed to create admin user: {str(e)}")


def show_migration_summary():
    """Display a summary of the database state."""
    print("\n" + "="*60)
    print("DATABASE MIGRATION SUMMARY")
    print("="*60)

    # Count users
    user_count = User.query.count()
    print(f"Users: {user_count}")

    # Count roles
    role_count = Role.query.count()
    roles = Role.query.all()
    print(f"Roles: {role_count}")
    for role in roles:
        print(f"  - {role.name}")

    # Count tokens
    refresh_token_count = RefreshToken.query.count()
    email_token_count = EmailVerificationToken.query.count()
    reset_token_count = PasswordResetToken.query.count()

    print(f"Refresh Tokens: {refresh_token_count}")
    print(f"Email Verification Tokens: {email_token_count}")
    print(f"Password Reset Tokens: {reset_token_count}")

    print("="*60)
    print("\n✓ Migration completed successfully!")
    print("\nNext steps:")
    print("  1. Update your .env file with SECRET_KEY and JWT_SECRET_KEY")
    print("  2. Start your Flask application")
    print("  3. Test the authentication endpoints at /api/auth/*")
    print("="*60 + "\n")


def main():
    """Main migration function."""
    print("\n" + "="*60)
    print("DATABASE MIGRATION - Authentication System")
    print("="*60 + "\n")

    app = create_app()

    with app.app_context():
        try:
            # Create tables
            create_tables()

            # Seed roles
            seed_roles()

            # Optionally create admin user
            create_admin_user()

            # Show summary
            show_migration_summary()

        except Exception as e:
            print(f"\n✗ Migration failed: {str(e)}")
            db.session.rollback()
            raise


if __name__ == '__main__':
    main()
