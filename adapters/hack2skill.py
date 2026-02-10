import requests
import hashlib
from datetime import datetime
from backend.schemas import Hackathon

BASE_URL = "https://vision.hack2skill.com/api/v1/innovator/public/event/public-list"


def fetch_hack2skill_hackathons(page: int = 1, records: int = 50) -> list[Hackathon]:
    """
    Fetches hackathons from Hack2Skill platform.

    Args:
        page: Page number to fetch (default: 1)
        records: Number of records per page (default: 50)

    Returns:
        List of Hackathon objects
    """
    try:
        # Set date range - from current date to 1 years in the future
        current_date = datetime.now()
        end_date = current_date.replace(year=current_date.year + 3)

        params = {
            "page": page,
            "records": records,
            "search": "",
            "start": current_date.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
            "end": end_date.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
        }

        response = requests.get(BASE_URL, params=params, timeout=10)
        response.raise_for_status()

        data = response.json()

        if not data.get("success"):
            print(f"API returned success=false: {data.get('message')}")
            return []

        events = data.get("data", [])
        hackathons = []

        for event in events:
            try:
                # Parse dates
                registration_start = event.get("registrationStart")
                registration_end = event.get("registrationEnd")
                submission_end = event.get("submissionEnd")

                # Use registration dates, fallback to submission dates if needed
                if registration_start:
                    start_date = datetime.fromisoformat(
                        registration_start.replace("Z", "+00:00")
                    ).date()
                else:
                    print(f"Skipping event {event.get('title')} - no registration start date")
                    continue

                # Prefer submission end over registration end for actual deadline
                if submission_end:
                    end_date = datetime.fromisoformat(submission_end.replace("Z", "+00:00")).date()
                elif registration_end:
                    end_date = datetime.fromisoformat(
                        registration_end.replace("Z", "+00:00")
                    ).date()
                else:
                    print(f"Skipping event {event.get('title')} - no end date")
                    continue

                # Skip if already ended
                if end_date < datetime.now().date():
                    continue

                # Determine location based on mode
                mode = event.get("mode", "VIRTUAL")
                if mode == "VIRTUAL":
                    location = "Online"
                elif mode == "HYBRID":
                    location = "Hybrid (Online + Offline)"
                else:
                    location = "Offline"

                # Build URL
                event_url = event.get("eventUrl", "")
                url = f"https://vision.hack2skill.com/event/{event_url}" if event_url else ""

                # Extract tags
                tags = []
                ticket_type = event.get("ticket")
                if ticket_type:
                    tags.append(ticket_type.capitalize())

                flag = event.get("flag")
                if flag:
                    tags.append(flag.capitalize())

                # Determine team size
                participation = event.get("participation", "")
                if participation == "Individual":
                    team_size = "Individual"
                elif participation == "Team":
                    team_size = "Team (size varies)"
                else:
                    team_size = "See details"

                # Determine status
                current_time = datetime.now().date()
                if start_date > current_time:
                    status = "Upcoming"
                elif start_date <= current_time <= end_date:
                    status = "Active"
                else:
                    status = "Ended"

                # Create hackathon object
                hackathon = Hackathon(
                    id=hashlib.sha256(event.get("_id", "").encode()).hexdigest(),
                    title=event.get("title", "Untitled Event"),
                    start_date=start_date,
                    end_date=end_date,
                    location=location,
                    url=url,
                    mode=mode.capitalize(),
                    status=status,
                    source="hack2skill",
                    tags=tags,
                    banner_url=event.get("thumbnail"),
                    prize_pool="See event page",  # API doesn't provide prize info
                    team_size=team_size,
                    eligibility="See event page",  # API doesn't provide eligibility info
                )

                hackathons.append(hackathon)

            except Exception as e:
                print(f"Error processing event {event.get('title', 'Unknown')}: {e}")
                continue

        return hackathons

    except requests.exceptions.RequestException as e:
        print(f"Error fetching Hack2Skill hackathons: {e}")
        return []
    except Exception as e:
        print(f"Unexpected error: {e}")
        import traceback

        traceback.print_exc()
        return []


if __name__ == "__main__":
    print("Fetching Hack2Skill hackathons...")
    hackathons = fetch_hack2skill_hackathons()
    print(f"\nFetched {len(hackathons)} hackathons.")

    for h in hackathons[:5]:
        print(f"\n- {h.title}")
        print(f"  Status: {h.status}")
        print(f"  Dates: {h.start_date} to {h.end_date}")
        print(f"  Mode: {h.mode} ({h.location})")
        print(f"  Team Size: {h.team_size}")
        print(f"  Tags: {', '.join(h.tags)}")
        print(f"  URL: {h.url}")
