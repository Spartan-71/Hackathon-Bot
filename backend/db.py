from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base 
from sqlalchemy.orm import sessionmaker
import os

DATABASE_URL = f"postgresql://{os.getenv("POSTGRES_USER")}:{os.getenv("POSTGRES_PASSWORD")}@db:5432/{os.getenv("POSTGRES_DB")}"
print(f"----------{DATABASE_URL}")


if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set")

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=300,
    pool_size=10,
    max_overflow=20,
    echo=False,  # Set to True for debugging SQL queries
    connect_args={
        "options": "-c timezone=utc -c statement_timeout=60000"
    }
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
