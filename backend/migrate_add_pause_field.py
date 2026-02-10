"""
Migration script to add notifications_paused field to guild_configs table.
Run this script once to update existing databases.
"""
from dotenv import load_dotenv
load_dotenv()  # Load environment variables from .env file

from backend.db import engine
from sqlalchemy import text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate():
    """Add notifications_paused column to guild_configs table if it doesn't exist."""
    try:
        with engine.connect() as conn:
            # Check if column exists
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='guild_configs' AND column_name='notifications_paused'
            """))
            
            if result.fetchone() is None:
                # Column doesn't exist, add it
                logger.info("Adding notifications_paused column to guild_configs table...")
                conn.execute(text("""
                    ALTER TABLE guild_configs 
                    ADD COLUMN notifications_paused VARCHAR DEFAULT 'false'
                """))
                conn.commit()
                logger.info("✅ Successfully added notifications_paused column")
            else:
                logger.info("ℹ️ notifications_paused column already exists, skipping migration")
                
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        raise

if __name__ == "__main__":
    migrate()
    print("\n✅ Migration completed successfully!")
