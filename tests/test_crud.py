from datetime import date, timedelta

from backend.crud import (
    get_all_subscriptions,
    get_guild_config,
    get_hackathons_by_platform,
    get_upcoming_hackathons,
    search_hackathons,
    pause_notifications,
    resume_notifications,
    subscribe_user,
    unsubscribe_user,
    update_guild_preferences,
    upsert_hackathon,
)
from backend.models import HackathonDB
from backend.schemas import Hackathon


def build_hackathon(
    hack_id: str,
    *,
    title: str = "AI Sprint",
    start_offset: int = 1,
    end_offset: int = 3,
    source: str = "devpost",
    tags: list[str] | None = None,
):
    today = date.today()
    return Hackathon(
        id=hack_id,
        title=title,
        start_date=today + timedelta(days=start_offset),
        end_date=today + timedelta(days=end_offset),
        location="Online",
        url=f"https://example.com/{hack_id}",
        mode="Online",
        status="Open",
        source=source,
        tags=tags or ["ai", "ml"],
        banner_url="https://example.com/banner.png",
        prize_pool="$10,000",
        team_size="1-4",
        eligibility="Students",
    )


def test_upsert_hackathon_create_and_update(db_session):
    hack = build_hackathon("hack-1", title="Original")

    created, is_new = upsert_hackathon(db_session, hack)
    assert is_new is True
    assert created.title == "Original"

    updated_hack = build_hackathon("hack-1", title="Updated Title", tags=["web", "cloud"])
    updated, is_new = upsert_hackathon(db_session, updated_hack)

    assert is_new is False
    assert updated.title == "Updated Title"
    assert updated.tags == "web,cloud"


def test_search_and_platform_and_upcoming_filters(db_session):
    upsert_hackathon(
        db_session, build_hackathon("hack-1", source="Devpost", tags=["ai", "web"], start_offset=1)
    )
    upsert_hackathon(
        db_session, build_hackathon("hack-2", source="Devfolio", tags=["data"], start_offset=2)
    )
    upsert_hackathon(
        db_session,
        build_hackathon("hack-3", source="Devpost", tags=["ai"], start_offset=-2, end_offset=1),
    )

    search_results = search_hackathons(db_session, "ai", limit=5)
    assert {r.id for r in search_results} == {"hack-1", "hack-3"}

    platform_results = get_hackathons_by_platform(db_session, "devpost", limit=10)
    assert [r.id for r in platform_results] == ["hack-1"]

    upcoming = get_upcoming_hackathons(db_session, days=2)
    assert [r.id for r in upcoming] == ["hack-1", "hack-2"]


def test_subscription_lifecycle(db_session):
    sub, is_new = subscribe_user(db_session, user_id=1001, theme="ai")
    assert is_new is True
    assert sub.theme == "ai"

    _, is_new_duplicate = subscribe_user(db_session, user_id=1001, theme="ai")
    assert is_new_duplicate is False

    all_subs = get_all_subscriptions(db_session)
    assert len(all_subs) == 1

    removed = unsubscribe_user(db_session, user_id=1001, theme="ai")
    assert removed is True
    assert get_all_subscriptions(db_session) == []

    removed_missing = unsubscribe_user(db_session, user_id=1001, theme="ai")
    assert removed_missing is False


def test_guild_preferences_pause_resume(db_session):
    config = update_guild_preferences(
        db_session,
        guild_id="guild-1",
        channel_id="channel-1",
        platforms=["devpost", "devfolio"],
        themes=["ai", "data"],
    )
    assert config.guild_id == "guild-1"
    assert config.subscribed_platforms == "devpost,devfolio"
    assert config.subscribed_themes == "ai,data"
    assert config.notifications_paused == "false"

    fetched = get_guild_config(db_session, "guild-1")
    assert fetched is not None
    assert fetched.channel_id == "channel-1"

    assert pause_notifications(db_session, "guild-1") is True
    assert get_guild_config(db_session, "guild-1").notifications_paused == "true"

    assert resume_notifications(db_session, "guild-1") is True
    assert get_guild_config(db_session, "guild-1").notifications_paused == "false"

    assert pause_notifications(db_session, "missing-guild") is False
    assert resume_notifications(db_session, "missing-guild") is False


def test_hackathon_rows_are_persisted(db_session):
    upsert_hackathon(db_session, build_hackathon("hack-9"))
    row = db_session.query(HackathonDB).filter(HackathonDB.id == "hack-9").first()
    assert row is not None
    assert row.source == "devpost"
