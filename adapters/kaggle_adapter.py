import os
import hashlib
from datetime import datetime
from dotenv import load_dotenv

# Load .env from the root directory
# env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv()

# Kaggle API expects KAGGLE_USERNAME and KAGGLE_KEY
# Map KAGGLE_API_TOKEN to KAGGLE_KEY if KAGGLE_KEY is not set
# Also strip 'KGAT_' prefix if present
# username = os.getenv("KAGGLE_USERNAME")
# key = os.getenv("KAGGLE_KEY") or os.getenv("KAGGLE_API_TOKEN")

# if key and key.startswith("KGAT_"):
#     key = key[5:]

# if key:
#     os.environ["KAGGLE_KEY"] = key
#     # Remove KAGGLE_API_TOKEN from environ to avoid confusion in the kaggle library
#     if "KAGGLE_API_TOKEN" in os.environ:
#         del os.environ["KAGGLE_API_TOKEN"]

# if username:
#     os.environ["KAGGLE_USERNAME"] = username

from kaggle.api.kaggle_api_extended import KaggleApi
from backend.schemas import Hackathon


def fetch_kaggle_competitions() -> list[Hackathon]:
    """
    Fetches active competitions from Kaggle using the official API.
    Requires KAGGLE_USERNAME and KAGGLE_KEY (or KAGGLE_API_TOKEN) environment variables.
    """
    # username = os.getenv("KAGGLE_USERNAME")
    # key = os.getenv("KAGGLE_KEY")

    # if not username or not key:
    #     print(f"Error: Kaggle credentials missing. Username: {username}, Key: {'set' if key else 'missing'}")
    #     return []

    try:
        api = KaggleApi()
        api.authenticate()
    except Exception as e:
        print(f"Error authenticating with Kaggle: {e}")
        return []
        
    # Fetch list of competitions
    # According to the API docs, we can filter by category and sort
    # Valid categories: all, featured, research, recruitment, gettingStarted, masters, playground
    # Valid sort options: latestDeadline, earliestDeadline, numberOfTeams, recentlyCreated, prize
    response = api.competitions_list(
        category='all',
        sort_by='latestDeadline',
        page=1
    )
    
    hackathons = []
    for comp in response.competitions:
        # Parse dates
        try:
            # The deadline field is a datetime string in ISO format
            deadline_str = comp.deadline
            if isinstance(deadline_str, str):
                end_date = datetime.fromisoformat(deadline_str.replace("Z", "+00:00")).date()
            else:
                end_date = deadline_str.date()
            
            # enabledDate is when the competition was enabled/started
            # Not all competitions have this field, so use getattr with default
            enabled_date_str = getattr(comp, 'enabledDate', None)
            if enabled_date_str:
                if isinstance(enabled_date_str, str):
                    start_date = datetime.fromisoformat(enabled_date_str.replace("Z", "+00:00")).date()
                else:
                    start_date = enabled_date_str.date()
            else:
                start_date = datetime.now().date()
            
            # Skip if ended
            if end_date < datetime.now().date():
                continue
                
        except Exception as e:
            print(f"Error parsing dates for {comp.title}: {e}")
            continue
        # Extract tags from the tags array
        tags = []
        
        for tag in comp.tags:
            # Each tag is an object with 'name' attribute
            tags.append(tag.name)
        # Team size from maxTeamSize
        team_size = "See details"
        team_size = f"1-{comp.max_team_size} members"
        
        # URL - use the url field directly
        url = comp.url if hasattr(comp, 'url') else f"https://www.kaggle.com/competitions/{comp.ref}"
        
        # Banner/thumbnail
        # banner_url = comp.thumbnailImageUrl
        
        
        hackathon = Hackathon(
            id=hashlib.sha256(str(comp.ref).encode()).hexdigest(),
            title=comp.title,
            start_date=start_date,
            end_date=end_date,
            location="Online",
            url=url,
            mode="Online",
            status="Active",
            source="kaggle",
            tags=tags,
            banner_url=None,
            prize_pool=comp.reward,
            team_size=team_size,
            eligibility="Open to all"
        )
        print(f"{hackathon} \n")
        hackathons.append(hackathon)
        
    return hackathons

if __name__ == "__main__":
    hacks = fetch_kaggle_competitions()
    print(f"Fetched {len(hacks)} competitions.")
    for h in hacks[:5]:
        print(f"- {h.title}")
        print(f"  Ends: {h.end_date}")
        print(f"  Prize: {h.prize_pool}")
        print(f"  Tags: {', '.join(h.tags[:3])}")
        print()
