import requests
import json
import hashlib
from datetime import datetime
from backend.schemas import Hackathon
from pydantic import ValidationError

def parse_unstop_date(date_str: str):
    """
    Parses date strings from Unstop API like:
    - '2025-07-19T00:00:00+05:30'
    """
    if not date_str or not isinstance(date_str, str):
        return None

    try:
        # Parse ISO format datetime
        dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        return dt.date()
    except (ValueError, TypeError):
        return None

def fetch_unstop_hackathons() -> list[Hackathon]:
    """
    Fetches and validates hackathon data from the Unstop API, fetching all pages.
    """
    base_url = "https://unstop.com/api/public/opportunity/search-result"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }

    hackathons = []
    page = 1
    
    while page is not None:
        params = {
            'opportunity': 'hackathons',
            'page': page,
            'oppstatus': 'open'
        }
        try:
            response = requests.get(base_url, headers=headers, params=params, timeout=10)
            if response.status_code != 200:
                print(f"Error: Received status code {response.status_code} on page {page}")
                break
            data = response.json()
            # Get last_page from the first response
            next_page_url= data.get("data", {}).get("next_page_url")
            if next_page_url:
                page = int(next_page_url.split("page=")[1])
            else:
                page = None
                break
            hackathon_data = data.get("data", {}).get("data", [])
        except requests.RequestException as e:
            print(f"Error fetching URL on page {page}: {e}")
            break
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON from response on page {page}: {e}")
            break

        for item in hackathon_data:
            # Extract start and end dates with fallbacks
            start_str = item.get("start_date")
            if not start_str:
                start_str = item.get("regnRequirements", {}).get("start_regn_dt")
            
            end_str = item.get("end_date")
            if not end_str:
                end_str = item.get("regnRequirements", {}).get("end_regn_dt")

            start_date = parse_unstop_date(start_str)
            end_date = parse_unstop_date(end_str)

            # If start_date is missing but we have end_date, use end_date as start_date (or today?)
            # Using end_date as start_date is safe to avoid validation error, 
            # but ideally we want the real start date. 
            # If both are None, it will be skipped by validation anyway.
            if start_date is None and end_date is not None:
                 start_date = end_date
            
            # Extract tags from filters
            tags = []
            for filter_item in item.get("filters", []):
                if filter_item.get("type") == "category":
                    tags.append(filter_item.get("name", ""))
            # Extract prizes
            prize_pool = "See details"
            prizes_data = item.get("prizes", [])
            if prizes_data:
                prize_list = []
                for p in prizes_data:
                    rank = p.get("rank", "")
                    cash = p.get("cash", "")
                    currency_icon = p.get("currency", "")
                    
                    currency = ""
                    if "rupee" in currency_icon:
                        currency = "₹"
                    elif "dollar" in currency_icon:
                        currency = "$"
                    elif "euro" in currency_icon:
                        currency = "€"
                    
                    if cash:
                        prize_list.append(f"{rank}: {currency}{cash}")
                    else:
                        prize_list.append(f"{rank}")
                
                if prize_list:
                    # Format as vertical list with bullet points
                    prize_pool = "\n".join([f"- {p}" for p in prize_list[:3]])
                    if len(prize_list) > 3:
                        prize_pool += "\n- ..."

            # Extract location
            region = item.get("region", "").lower()
            location = "Online" if region == "online" else "Everywhere"
            
            addr = item.get("address_with_country_logo")
            if addr:
                parts = []
                for key in ["address", "city", "state"]:
                    val = addr.get(key)
                    if val:
                        parts.append(val)
                
                country = addr.get("country", {}).get("name")
                if country:
                    parts.append(country)
                
                if parts:
                    location = ", ".join(parts)

            # Map status
            reg_status = item.get("regnRequirements", {}).get("reg_status", "").upper()
            opp_status = item.get("status", "").upper()
            
            status = "ongoing"
            if reg_status == "FINISHED":
                status = "closed"
            elif reg_status == "YET_TO_START":
                status = "upcoming"
            elif opp_status == "LIVE":
                status = "ongoing"

            try:
                hackathon = Hackathon(
                    id=hashlib.sha256(str(item.get("title")).encode()).hexdigest(),
                    title=item.get("title"),
                    start_date=start_date,
                    end_date=end_date,
                    location=location,
                    url=item.get("seo_url"),
                    mode=item.get("region"),
                    status=status,
                    source="unstop",
                    tags=tags,
                    banner_url=item.get("logoUrl2"),
                    prize_pool=prize_pool,
                    team_size=f"{item.get('regnRequirements', {}).get('min_team_size', 1)}-{item.get('regnRequirements', {}).get('max_team_size', 1)} members",
                    eligibility=", ".join([f.get("name", "") for f in item.get("filters", []) if f.get("type") == "eligible"]) or "Open to all"
                )
                hackathons.append(hackathon)
            except ValidationError as e:
                print(f"Skipping hackathon due to validation error: {item.get('title')}")
                print(e)
    return hackathons

if __name__ == "__main__":
    hackathons = fetch_unstop_hackathons()
    