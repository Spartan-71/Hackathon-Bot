from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os

DATABASE_URL = os.getenv("DATABASE_URL")


if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set")

is_sqlite = DATABASE_URL.startswith("sqlite")
engine_kwargs = {
    "pool_pre_ping": True,
    "echo": False,  # Set to True for debugging SQL queries
}

if is_sqlite:
    # SQLite does not support PostgreSQL connection options or queue pool args.
    engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    engine_kwargs["pool_recycle"] = 300
    engine_kwargs["pool_size"] = 10
    engine_kwargs["max_overflow"] = 20
    engine_kwargs["connect_args"] = {"options": "-c timezone=utc -c statement_timeout=60000"}

engine = create_engine(DATABASE_URL, **engine_kwargs)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
