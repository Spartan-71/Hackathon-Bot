from sqlalchemy import Column, String, Date, Text, Integer, BigInteger, TIMESTAMP, func, UniqueConstraint, Index
from backend.db import Base


class HackathonDB(Base):
    __tablename__ = "hackathons"

    id = Column(String, primary_key=True, index=True)
    title = Column(String, nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    location = Column(String,nullable=False)
    url = Column(String, nullable=False)
    mode = Column(String,nullable=False)
    status = Column(String,nullable=False)
    source = Column(String, nullable=False)
    tags = Column(Text, default="",nullable=True)
    banner_url = Column(String, nullable=True)
    prize_pool = Column(String, nullable=True)
    team_size = Column(String, nullable=True)
    eligibility = Column(String, nullable=True)


    def __repr__(self):
        return f"<Hackathon(title='{self.title}', start_date='{self.start_date}')>"


class GuildConfig(Base):
    __tablename__ = "guild_configs"

    guild_id = Column(String, primary_key=True, index=True)
    channel_id = Column(String, nullable=False)
    subscribed_platforms = Column(String, default="all")  
    subscribed_themes = Column(String, default="all")
    
    def __repr__(self):
        return f"<GuildConfig(guild_id='{self.guild_id}', channel_id='{self.channel_id}')>"


class UserSubscription(Base):
    __tablename__ = "user_subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(BigInteger, nullable=False)
    theme = Column(String(100), nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())

    __table_args__ = (
        UniqueConstraint('user_id', 'theme', name='unique_user_theme'),
        Index('idx_user_subscriptions_user_id', 'user_id'),
    )

    def __repr__(self):
        return f"<UserSubscription(user_id={self.user_id}, theme='{self.theme}')>"