#!/usr/bin/env python3
"""
Superset initialization script to add PostgreSQL database connection
"""
import os
import sys

# Add Superset to path
sys.path.insert(0, '/app')

try:
    # Import app factory first
    from superset.app import create_app
    
    # Create app with proper context
    app = create_app()
    
    with app.app_context():
        from superset import db
        from superset.models.core import Database
        
        # Get PostgreSQL connection details from environment
        postgres_host = os.environ.get('POSTGRES_HOST', 'postgres')
        postgres_port = os.environ.get('POSTGRES_PORT', '5432')
        postgres_user = os.environ.get('POSTGRES_USER', 'ubidex')
        postgres_password = os.environ.get('POSTGRES_PASSWORD', 'ubidex')
        postgres_db = os.environ.get('POSTGRES_DB', 'ubidex')
        
        db_name = 'Ubidex Events DB'
        
        # Build PostgreSQL URI
        postgres_uri = f"postgresql://{postgres_user}:{postgres_password}@{postgres_host}:{postgres_port}/{postgres_db}"
        
        # Check if database connection already exists (using SQLAlchemy 2.0 syntax)
        existing_db = db.session.query(Database).filter_by(database_name=db_name).first()
        
        if not existing_db:
            print(f"Creating database connection: {db_name}")
            print(f"PostgreSQL: {postgres_host}:{postgres_port}/{postgres_db}")
            
            database = Database(
                database_name=db_name,
                sqlalchemy_uri=postgres_uri,
            )
            db.session.add(database)
            db.session.commit()
            print(f"Database connection created successfully!")
        else:
            print(f"Database connection already exists: {db_name}")
            # Update URI if connection changed
            if existing_db.sqlalchemy_uri != postgres_uri:
                existing_db.sqlalchemy_uri = postgres_uri
                db.session.commit()
                print(f"Database URI updated")
                
except Exception as e:
    print(f"Error initializing Superset database connection: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

