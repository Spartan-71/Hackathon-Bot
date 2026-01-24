from sqlalchemy.orm import Session
from sqlalchemy import or_
from sqlalchemy.exc import SQLAlchemyError
from backend.models import HackathonDB, UserSubscription, GuildConfig
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

def search_hackathons(db: Session, keyword: str, limit: int = 3):
    try:
        # Case insensitive search using ilike
        search_term = f"%{keyword}%"
        results = db.query(HackathonDB).filter(HackathonDB.tags.ilike(search_term)).limit(limit).all()
        return results
    except SQLAlchemyError as e:
        logging.error(f"Database error in search_hackathons: {e}")
        return []

from datetime import date

def get_hackathons_by_platform(db: Session, platform_name: str, limit: int = 3):
    """
    Get hackathons from a specific platform (source).
    Returns upcoming hackathons ordered by start date (soonest first).
    """
    try:
        # Case insensitive search on the source column
        # Filter for hackathons starting today or in the future
        # Order by start_date ascending (soonest first)
        results = db.query(HackathonDB)\
            .filter(HackathonDB.source.ilike(f"%{platform_name}%"))\
            .filter(HackathonDB.start_date >= date.today())\
            .order_by(HackathonDB.start_date.asc())\
            .limit(limit).all()
        return results
    except SQLAlchemyError as e:
        logging.error(f"Database error in get_hackathons_by_platform: {e}")
        return []

from datetime import timedelta

def get_upcoming_hackathons(db: Session, days: int = 7):
    """
    Get hackathons starting within the next 'days' days.
    """
    try:
        today = date.today()
        end_date = today + timedelta(days=days)
        
        results = db.query(HackathonDB)\
            .filter(HackathonDB.start_date >= today)\
            .filter(HackathonDB.start_date <= end_date)\
            .order_by(HackathonDB.start_date.asc())\
            .all()
        return results
    except SQLAlchemyError as e:
        logging.error(f"Database error in get_upcoming_hackathons: {e}")
        return []

def subscribe_user(db: Session, user_id: int, theme: str):
    """
    Subscribe a user to a theme.
    Returns (subscription_obj, is_new)
    """
    try:
        # Normalize theme to lowercase for consistent matching? 
        # The user didn't specify, but it's good practice. 
        # However, tags in DB might be mixed case. 
        # Let's store as provided but maybe lowercase for comparison?
        # For now, store as provided.
        
        existing = db.query(UserSubscription).filter_by(user_id=user_id, theme=theme).first()
        if existing:
            return existing, False
        
        sub = UserSubscription(user_id=user_id, theme=theme)
        db.add(sub)
        db.commit()
        db.refresh(sub)
        return sub, True
    except SQLAlchemyError as e:
        db.rollback()
        logging.error(f"Database error in subscribe_user: {e}")
        raise

def unsubscribe_user(db: Session, user_id: int, theme: str):
    """
    Unsubscribe a user from a theme.
    Returns True if removed, False if not found.
    """
    try:
        existing = db.query(UserSubscription).filter_by(user_id=user_id, theme=theme).first()
        if existing:
            db.delete(existing)
            db.commit()
            return True
        return False
    except SQLAlchemyError as e:
        db.rollback()
        logging.error(f"Database error in unsubscribe_user: {e}")
        raise


def get_all_subscriptions(db: Session):
    """
    Get all user subscriptions.
    """
    try:
        return db.query(UserSubscription).all()
    except SQLAlchemyError as e:
        logging.error(f"Database error in get_all_subscriptions: {e}")
        return []

def get_user_subscriptions(db: Session, user_id: int):
    """
    Get all subscriptions for a specific user.
    """
    try:
        return db.query(UserSubscription).filter(UserSubscription.user_id == user_id).all()
    except SQLAlchemyError as e:
        logging.error(f"Database error in get_user_subscriptions: {e}")
        return []

def get_guild_config(db: Session, guild_id: str):
    """
    Get guild configuration.
    """
    try:
        return db.query(GuildConfig).filter(GuildConfig.guild_id == guild_id).first()
    except SQLAlchemyError as e:
        logging.error(f"Database error in get_guild_config: {e}")
        return None

def update_guild_preferences(db: Session, guild_id: str, channel_id: str = None, platforms: list = None, themes: list = None):
    """
    Update guild preferences.
    """
    try:
        config = db.query(GuildConfig).filter(GuildConfig.guild_id == guild_id).first()
        if not config:
            config = GuildConfig(guild_id=guild_id)
            db.add(config)
        
        if channel_id:
            config.channel_id = channel_id
        
        if platforms is not None:
            config.subscribed_platforms = ",".join(platforms) if platforms else "all"
            
        if themes is not None:
            config.subscribed_themes = ",".join(themes) if themes else "all"
            
        db.commit()
        db.refresh(config)
        return config
    except SQLAlchemyError as e:
        db.rollback()
        logging.error(f"Database error in update_guild_preferences: {e}")
        raise

def pause_notifications(db: Session, guild_id: str):
    """
    Pause notifications for a guild.
    Returns True if successful, False if guild config doesn't exist.
    """
    try:
        config = db.query(GuildConfig).filter(GuildConfig.guild_id == guild_id).first()
        if not config:
            return False
        
        config.notifications_paused = "true"
        db.commit()
        return True
    except SQLAlchemyError as e:
        db.rollback()
        logging.error(f"Database error in pause_notifications: {e}")
        raise

def resume_notifications(db: Session, guild_id: str):
    """
    Resume notifications for a guild.
    Returns True if successful, False if guild config doesn't exist.
    """
    try:
        config = db.query(GuildConfig).filter(GuildConfig.guild_id == guild_id).first()
        if not config:
            return False
        
        config.notifications_paused = "false"
        db.commit()
        return True
    except SQLAlchemyError as e:
        db.rollback()
        logging.error(f"Database error in resume_notifications: {e}")
        raise