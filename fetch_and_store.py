import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from sqlalchemy.exc import SQLAlchemyError, OperationalError
from adapters.devpost import fetch_devpost_hackathons
from adapters.unstop import fetch_unstop_hackathons
from adapters.dorahacks import fetch_dorahacks_hackathons
from adapters.mlh import scrape_mlh_events
from adapters.devfolio import fetch_devfolio_hackathons

from backend.db import SessionLocal, Base, engine
from backend.crud import upsert_hackathon

Base.metadata.create_all(bind=engine)

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

def process_source(source_name, fetch_func):
    """Process a single source with its own database session. Returns list of newly added hackathons."""
    max_retries = 3
    retry_delay = 1
    new_hackathons = []
    
    for attempt in range(max_retries):
        db = SessionLocal()
        try:
            logging.info(f"Started fetching from {source_name}.")
            hackathons = fetch_func()
            logging.info(f"Fetched {len(hackathons)} hackathons from {source_name}.")
            
            for h in hackathons:
                try:
                    logging.debug(f"Upserting hackathon: {h}")
                    db_obj, is_new = upsert_hackathon(db, h)
                    if is_new:
                        new_hackathons.append(h)
                except (SQLAlchemyError, OperationalError) as e:
                    logging.error(f"Database error upserting hackathon from {source_name}: {e}")
                    db.rollback()
                    continue
                except Exception as e:
                    logging.error(f"Unexpected error upserting hackathon from {source_name}: {e}")
                    db.rollback()
                    continue
            
            logging.info(f"Completed upserting hackathons from {source_name}. {len(new_hackathons)} new hackathons added.")
            break  # Success, exit retry loop
            
        except (SQLAlchemyError, OperationalError) as e:
            logging.error(f"Database error fetching from {source_name} (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                logging.error(f"Failed to process {source_name} after {max_retries} attempts")
        except Exception as e:
            logging.error(f"Error fetching from {source_name}: {e}")
            break  # Don't retry for non-database errors
        finally:
            db.close()
    
    return new_hackathons

def run():
    """
    Run hackathon scraping and return list of newly added hackathons.
    Returns: List of Hackathon objects that were newly added to the database.
    """
    logging.info("Starting hackathon scraping run.")
    sources = [
        ("MLH", scrape_mlh_events),
        ("Devpost", fetch_devpost_hackathons),
        ("Unstop", fetch_unstop_hackathons),
        ("DoraHacks", fetch_dorahacks_hackathons),
        ("Devfolio", fetch_devfolio_hackathons),
    ]
    all_new_hackathons = []
    
    with ThreadPoolExecutor(max_workers=len(sources)) as executor:
        future_to_source = {executor.submit(process_source, name, fetch_func): name for name, fetch_func in sources}
        for future in as_completed(future_to_source):
            name = future_to_source[future]
            try:
                new_hackathons = future.result()  # Get list of new hackathons from this source
                all_new_hackathons.extend(new_hackathons)
            except Exception as e:
                logging.error(f"Thread for {name} failed: {e}")
    
    logging.info(f"Hackathon scraping run completed. {len(all_new_hackathons)} new hackathons added.")
    return all_new_hackathons


if __name__ == "__main__":
    run()
