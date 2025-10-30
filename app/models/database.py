from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# Create the database directory if it doesn't exist
db_dir = os.path.join(os.path.dirname(__file__), "..")
db_path = os.path.join(db_dir, "database.db")
os.makedirs(db_dir, exist_ok=True)

# Use SQLite for simplicity, store in app directory
DATABASE_URL = f"sqlite:///{db_path}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()