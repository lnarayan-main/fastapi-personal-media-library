# backend/database.py
import os
from sqlmodel import create_engine, SQLModel, Session
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

# Create the engine
engine = create_engine(DATABASE_URL, echo=True, pool_recycle=3600)

def create_db_and_tables():
    """Initializes the database and creates all tables from models package"""
    # Importing models package ensures SQLModel metadata is populated
    import models  # noqa: F401
    SQLModel.metadata.create_all(engine)

# Dependency to get a database session
def get_session():
    """Provides a transactional database session."""
    with Session(engine) as session:
        yield session
