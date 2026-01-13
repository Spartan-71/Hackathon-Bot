from sqlalchemy.orm import Session
from sqlalchemy import or_
from sqlalchemy.exc import SQLAlchemyError
from backend.models import HackathonDB
from backend.schemas import Hackathon
import logging

def upsert_hackathon(db: Session, hack: Hackathon):
    """
    Upsert a hackathon and return (hackathon_obj, is_new)
    where is_new is True if the hackathon was newly created, False if updated
    """
    try:
        db_obj = db.query(HackathonDB).filter_by(id=hack.id).first()
        if db_obj:
            # Update existing record if needed
            db_obj.title = hack.title
            db_obj.start_date = hack.start_date
            db_obj.end_date = hack.end_date
            db_obj.location = hack.location
            db_obj.url = hack.url
            db_obj.mode = hack.mode
            db_obj.status = hack.status
            db_obj.source = hack.source
            db_obj.tags = ",".join(hack.tags)
            db_obj.banner_url = hack.banner_url
            db_obj.prize_pool = hack.prize_pool
            db_obj.team_size = hack.team_size
            db_obj.eligibility = hack.eligibility
            db.commit()
            return db_obj, False
        else:
            # Create new record
            db_obj = HackathonDB(
                id=hack.id,
                title=hack.title,
                start_date=hack.start_date,
                end_date=hack.end_date,
                location=hack.location,
                url=hack.url,
                mode=hack.mode,
                status=hack.status, 
                source=hack.source,
                tags=",".join(hack.tags),
                banner_url=hack.banner_url,
                prize_pool=hack.prize_pool,
                team_size=hack.team_size,
                eligibility=hack.eligibility
            )
            db.add(db_obj)
            db.commit()
            db.refresh(db_obj)
            return db_obj, True
    except SQLAlchemyError as e:
        db.rollback()
        logging.error(f"Database error in upsert_hackathon: {e}")
        raise
    except Exception as e:
        db.rollback()
        logging.error(f"Unexpected error in upsert_hackathon: {e}")
        raise
    
def get_upcoming(db: Session, from_date=None, to_date=None, sources=None):
    try:
        q = db.query(HackathonDB)
        if from_date:
            q = q.filter(HackathonDB.start_date >= from_date)
        if to_date:
            q = q.filter(HackathonDB.end_date <= to_date)
        if sources:
            q = q.filter(HackathonDB.source.in_(sources))
        return q.order_by(HackathonDB.start_date).all()
    except SQLAlchemyError as e:
        logging.error(f"Database error in get_upcoming: {e}")
        raise

def search_hackathons(db: Session, keyword: str, limit: int = 5):
    try:
        # Case insensitive search using ilike
        search_term = f"%{keyword}%"
        results = db.query(HackathonDB).filter(HackathonDB.tags.ilike(search_term)).limit(limit).all()
        return results
    except SQLAlchemyError as e:
        logging.error(f"Database error in search_hackathons: {e}")
        return []