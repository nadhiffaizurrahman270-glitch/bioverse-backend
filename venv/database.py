import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Ambil konfigurasi DB dari .env atau default
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql://postgres:afterngopi8@localhost:5432/bioverse_db" # Ganti password 'root' jika beda
)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()