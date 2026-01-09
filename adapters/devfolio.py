import requests
import hashlib
from backend.schemas import Hackathon
from datetime import datetime

def fetch_devfolio_hackathons():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    hackathons = []
    page = 1
    while True:
        try:
            response = requests.get(
                "https://api.devfolio.co/api/hackathons",
                params={"filter": "application_open", "page": page},
                headers=headers
            )
            response.raise_for_status()
            data = response.json()
            
            if "result" not in data or not data["result"]:
                break
                
            for item in data["result"]:
                title = item.get("name")
                slug = item.get("slug")
                url = f"https://{slug}.devfolio.co/" if slug else None
                
                start_str = item.get("starts_at")
                end_str = item.get("ends_at")
                
                start_date = None
                end_date = None
                
                if start_str:
                    try:
                        start_date = datetime.fromisoformat(start_str.replace("Z", "+00:00")).date()
                    except ValueError:
                        pass
                        
                if end_str:
                    try:
                        end_date = datetime.fromisoformat(end_str.replace("Z", "+00:00")).date()
                    except ValueError:
                        pass
                
                # Determine status based on dates
                status = "Open"
                today = datetime.now().date()
                if start_date and end_date:
                    if today > end_date:
                        status = "Ended"
                    elif today >= start_date:
                        status = "Live"
                    else:
                        status = "Upcoming" # or Open for registration
                
                # Since we are filtering by 'application_open', they are likely Open/Upcoming
                # But let's stick to a simple mapping if needed, or just use the calculated one.
                
                if title and start_date and end_date and url:
                    hackathon = Hackathon(
                        id=hashlib.sha256(title.encode()).hexdigest(),
                        title=title,
                        start_date=start_date,
                        end_date=end_date,
                        location=item.get("location") or "Everywhere",
                        url=url,
                        mode="Online" if item.get("is_online") else "Offline",
                        status=status,
                        source="Devfolio"
                    )
                    hackathons.append(hackathon)
                    
            page += 1
            
        except requests.exceptions.RequestException as e:
            print(f"Error fetching page {page}: {e}")
            break
            
    return hackathons


if __name__ == "__main__":
    scarpe_devfolio_hackathons()

