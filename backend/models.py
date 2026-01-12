from sqlalchemy import Column, String, Date, Text
from backend.db import Base


class HackathonDB(Base):
    __tablename__ = "hackathons"

    id = Column(String, primary_key=True, index=True)
    title = Column(String, nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    location = Column(String,nullable=False)
    url = Column(String, unique=True, nullable=False)
    mode = Column(String,nullable=False)
    status = Column(String,nullable=False)
    source = Column(String, nullable=False)
    tags = Column(Text, default="",nullable=True)
    banner_url = Column(String, nullable=True)


    def __repr__(self):
        return f"<Hackathon(title='{self.title}', start_date='{self.start_date}')>"


class GuildConfig(Base):
    __tablename__ = "guild_configs"

    guild_id = Column(String, primary_key=True, index=True)
    channel_id = Column(String, nullable=False)

    def __repr__(self):
        return f"<GuildConfig(guild_id='{self.guild_id}', channel_id='{self.channel_id}')>"