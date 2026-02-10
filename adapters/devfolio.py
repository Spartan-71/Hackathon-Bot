import requests
import hashlib
from backend.schemas import Hackathon
from datetime import datetime


def fetch_devfolio_hackathons():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    hackathons = []
    page = 1
    while True:
        try:
            response = requests.get(
                "https://api.devfolio.co/api/hackathons",
                params={"filter": "application_open", "page": page},
                headers=headers,
            )
            response.raise_for_status()
            data = response.json()

            if "result" not in data or not data["result"]:
                break

            for item in data["result"]:
                title = item.get("name")
                slug = item.get("slug")
                url = f"https://{slug}.devfolio.co/" if slug else None
                banner_link = item.get("cover_img")
                start_str = item.get("starts_at")
                end_str = item.get("ends_at")
                registation_link = f"{url}/application"

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
                        status = "Upcoming"  # or Open for registration

                # Since we are filtering by 'application_open', they are likely Open/Upcoming
                # But let's stick to a simple mapping if needed, or just use the calculated one.

                # Fetch prizes
                prize_pool = "See details"
                try:
                    prizes_url = f"https://api.devfolio.co/api/hackathons/{slug}/prizes"
                    prizes_resp = requests.get(prizes_url, headers=headers, timeout=5)
                    if prizes_resp.status_code == 200:
                        prizes_data = prizes_resp.json()
                        if prizes_data:
                            prize_list = []
                            for p in prizes_data:
                                p_name = p.get("name", "")
                                p_amount = p.get("amount")
                                p_desc = p.get("desc", "")
                                if p_amount and float(p_amount) > 0:
                                    prize_list.append(f"{p_name}: ${p_amount}")
                                elif p_desc:
                                    # If no amount, maybe use description or just name
                                    prize_list.append(f"{p_name}")

                            if prize_list:
                                # Format as vertical list with bullet points
                                prize_pool = "\n".join([f"- {p}" for p in prize_list[:3]])
                                if len(prize_list) > 3:
                                    prize_pool += "\n- ..."
                except Exception as e:
                    print(f"Error fetching prizes for {slug}: {e}")

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
                        source="devfolio",
                        banner_url=banner_link,
                        registation_link=registation_link,
                        prize_pool=prize_pool,
                        team_size=f"{item.get('team_min', 1)}-{item.get('team_size', 4)} members",
                        eligibility="Open to all",  # Devfolio is generally open, API doesn't specify restrictions clearly in list
                    )
                    hackathons.append(hackathon)

            page += 1

        except requests.exceptions.RequestException as e:
            print(f"Error fetching page {page}: {e}")
            break

    return hackathons


if __name__ == "__main__":
    fetch_devfolio_hackathons()
