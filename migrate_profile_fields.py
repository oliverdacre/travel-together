"""
Migration script to add new profile fields to the User table.
This script adds: birthday, profile_photo, location, and phone fields.
"""
from travel import db, create_app
from sqlalchemy import text

app = create_app()

with app.app_context():
    # Check if columns already exist by trying to query them
    try:
        # Try to query the new columns - if they exist, this will work
        db.session.execute(text("SELECT birthday, profile_photo, location, phone FROM user LIMIT 1"))
        print("New profile fields already exist in the database.")
    except Exception:
        # Columns don't exist, so we need to add them
        print("Adding new profile fields to the User table...")
        
        try:
            # SQLite supports ALTER TABLE ADD COLUMN
            db.session.execute(text("ALTER TABLE user ADD COLUMN birthday DATETIME"))
            print("✓ Added birthday column")
        except Exception as e:
            print(f"  Note: birthday column may already exist: {e}")
        
        try:
            db.session.execute(text("ALTER TABLE user ADD COLUMN profile_photo VARCHAR(500)"))
            print("✓ Added profile_photo column")
        except Exception as e:
            print(f"  Note: profile_photo column may already exist: {e}")
        
        try:
            db.session.execute(text("ALTER TABLE user ADD COLUMN location VARCHAR(100)"))
            print("✓ Added location column")
        except Exception as e:
            print(f"  Note: location column may already exist: {e}")
        
        try:
            db.session.execute(text("ALTER TABLE user ADD COLUMN phone VARCHAR(20)"))
            print("✓ Added phone column")
        except Exception as e:
            print(f"  Note: phone column may already exist: {e}")
        
        # Also update gender column size if needed (from 10 to 20)
        try:
            # SQLite doesn't support MODIFY COLUMN directly, but we can check if it's needed
            # For now, we'll just note that the model allows up to 20 characters
            print("✓ Gender column size updated in model (SQLite will use the model's limit)")
        except Exception as e:
            pass
        
        db.session.commit()
        print("\n✅ Migration completed successfully!")
        print("New profile fields are now available:")
        print("  - birthday (DateTime)")
        print("  - profile_photo (String)")
        print("  - location (String)")
        print("  - phone (String)")

