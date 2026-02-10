import requests
import hashlib
from backend.schemas import Hackathon
from datetime import datetime


def fetch_dorahacks_hackathons() -> list[Hackathon]:
    base_url = "https://dorahacks.io/api/hackathon/"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36"
    }

    try:
        all_hackathons = []
        # Fetch upcoming and ongoing hackathons with pagination
        for status in ["upcoming", "ongoing"]:
            url = base_url
            params = {"page": 1, "page_size": 24, "status": status}

            while url:
                response = requests.get(url, params=params, headers=headers)
                response.raise_for_status()
                data = response.json()

                all_hackathons.extend(data.get("results", []))

                # Get the next page URL, if it exists
                url = data.get("next")
                # Subsequent requests use the full URL from 'next', so we clear params
                params = None

        hackathons_data = []
        for hack in all_hackathons:
            start_date = (
                datetime.fromtimestamp(hack.get("start_time")) if hack.get("start_time") else None
            )
            end_date = (
                datetime.fromtimestamp(hack.get("end_time")) if hack.get("end_time") else None
            )

            curr_status = hack.get("status")
            status = "upcoming" if curr_status == 0 else "ongoing"
            mode = "Online" if hack.get("participation_form") == "Virtual" else "Offline"
            location = "Everywhere" if not hack.get("venue_name") else hack.get("venue_name")

            # Fetch prizes
            prize_pool = "See details"
            try:
                # DoraHacks doesn't have a specific prizes endpoint, but the detail endpoint has 'amount' and 'token'
                # or sometimes it's in the description.
                # Based on analysis, 'amount' (bonus_price in some contexts) seems to be the total prize pool.
                # Let's fetch details by ID to be sure, or use the list item if available.

                # The list item 'hack' might already have it?
                # In the list response (from previous analysis), we didn't see 'amount' directly.
                # But let's try to fetch details if we want to be accurate.
                # However, to avoid too many requests, let's check if 'bonus_price' or similar is in 'hack' object first.

                amount = hack.get("bonus_price")
                token = hack.get("token", "USD")

                if amount:
                    prize_pool = f"- Total: {amount} {token}"
                else:
                    # If not in list, try detail fetch (optional, might slow down)
                    # For now, let's stick to list data if possible to avoid 20+ requests per run.
                    # If 'bonus_price' is 0 or missing, we default to "See details".
                    pass

            except Exception as e:
                print(f"Error processing prizes for {hack.get('title')}: {e}")

            hackathon = Hackathon(
                id=hashlib.sha256(hack.get("title").encode()).hexdigest(),
                title=hack.get("title"),
                start_date=start_date.date() if start_date else None,
                end_date=end_date.date() if end_date else None,
                location=location,
                url=f"https://dorahacks.io/hackathon/{hack.get('uname')}/detail",
                mode=mode,
                status=status,
                source="dorahacks",
                tags=hack.get("field"),
                banner_url=hack.get("image_url"),
                prize_pool=prize_pool,
                team_size="See details",
                eligibility="See details",
            )
            hackathons_data.append(hackathon)
        return hackathons_data
    except requests.exceptions.RequestException as e:
        print(f"Error fetching hackathons from DoraHacks: {e}")
        return []


if __name__ == "__main__":
    fetch_dorahacks_hackathons()
