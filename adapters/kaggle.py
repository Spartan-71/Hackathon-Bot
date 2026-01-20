import os
import hashlib
from datetime import datetime
from kaggle.api.kaggle_api_extended import KaggleApi
from backend.schemas import Hackathon

def fetch_kaggle_competitions() -> list[Hackathon]:
    """
    Fetches active competitions from Kaggle using the official API.
    Requires KAGGLE_API_TOKEN environment variable to be set.
    
    Authentication can be done via:
    1. KAGGLE_API_TOKEN environment variable
    2. ~/.kaggle/access_token file
    3. ~/.kaggle/kaggle.json file (legacy)
    """
    try:
        api = KaggleApi()
        api.authenticate()
        
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
                source="Kaggle",
                tags=tags,
                banner_url=None,
                prize_pool=comp.reward,
                team_size=team_size,
                eligibility="Open to all"
            )
            print(f"{hackathon} /n")
            hackathons.append(hackathon)
            
        return hackathons

    except Exception as e:
        print(f"Error fetching Kaggle competitions: {e}")
        import traceback
        traceback.print_exc()
        return []

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    
    hacks = fetch_kaggle_competitions()
    print(f"Fetched {len(hacks)} competitions.")
    for h in hacks[:5]:
        print(f"- {h.title}")
        print(f"  Ends: {h.end_date}")
        print(f"  Prize: {h.prize_pool}")
        print(f"  Tags: {', '.join(h.tags[:3])}")
        print()
