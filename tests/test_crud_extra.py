from datetime import date, timedelta

from backend.crud import (
    get_upcoming,
    get_user_subscriptions,
    subscribe_user,
    update_guild_preferences,
    upsert_hackathon,
)
from backend.schemas import Hackathon


def build_hackathon(hack_id: str, *, source: str, start_offset: int, end_offset: int):
    today = date.today()
    return Hackathon(
        id=hack_id,
        title=f"Hack {hack_id}",
        start_date=today + timedelta(days=start_offset),
        end_date=today + timedelta(days=end_offset),
        location="Online",
        url=f"https://example.com/{hack_id}",
        mode="Online",
        status="Open",
        source=source,
        tags=["ai"],
    )


def test_get_upcoming_filters_by_dates_and_sources(db_session):
    upsert_hackathon(
        db_session, build_hackathon("g1", source="devpost", start_offset=1, end_offset=2)
    )
    upsert_hackathon(
        db_session, build_hackathon("g2", source="devfolio", start_offset=3, end_offset=5)
    )
    upsert_hackathon(
        db_session, build_hackathon("g3", source="kaggle", start_offset=7, end_offset=8)
    )

    today = date.today()
    results = get_upcoming(
        db_session,
        from_date=today + timedelta(days=1),
        to_date=today + timedelta(days=6),
        sources=["devpost", "devfolio"],
    )

    assert [r.id for r in results] == ["g1", "g2"]


def test_get_user_subscriptions_filters_single_user(db_session):
    subscribe_user(db_session, user_id=10, theme="ai")
    subscribe_user(db_session, user_id=10, theme="web")
    subscribe_user(db_session, user_id=20, theme="cloud")

    user_10 = get_user_subscriptions(db_session, 10)
    user_20 = get_user_subscriptions(db_session, 20)

    assert sorted(s.theme for s in user_10) == ["ai", "web"]
    assert [s.theme for s in user_20] == ["cloud"]


def test_update_guild_preferences_empty_lists_fall_back_to_all(db_session):
    config = update_guild_preferences(
        db_session,
        guild_id="guild-extra",
        channel_id="chan-1",
        platforms=[],
        themes=[],
    )

    assert config.channel_id == "chan-1"
    assert config.subscribed_platforms == "all"
    assert config.subscribed_themes == "all"
