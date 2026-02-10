from pydantic import BaseModel, field_validator
from datetime import date
from typing import List


class Hackathon(BaseModel):
    id: str
    title: str
    start_date: date
    end_date: date
    location: str
    url: str
    mode: str
    status: str
    source: str
    tags: List[str] = []
    banner_url: str | None = None
    prize_pool: str | None = None
    team_size: str | None = None
    eligibility: str | None = None

    @field_validator("tags", mode="before")
    @classmethod
    def split_tags(cls, v):
        if isinstance(v, str):
            return [tag.strip().lower() for tag in v.split(",") if tag.strip()]
        return v

    model_config = {"from_attributes": True}
