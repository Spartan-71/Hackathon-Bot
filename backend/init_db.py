from backend.db import Base, engine


def create_all_tables():
    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    create_all_tables()
