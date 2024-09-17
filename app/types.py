import enum
from typing import Tuple

from pydantic import BaseModel


class Headline(BaseModel):
    id: str
    title: str
    summary: str
    publication: str
    category: str


class HeadlineStoryQueryStrategy(enum.Enum):
    USE_TITLE = enum.auto()
    USE_SUMMARY = enum.auto()
    USE_TITLE_AND_SUMMARY = enum.auto()

    @staticmethod
    def from_user_str(user_str: str) -> "HeadlineStoryQueryStrategy":
        if user_str == "match-on-title":
            return HeadlineStoryQueryStrategy.USE_TITLE
        elif user_str == "match-on-summary":
            return HeadlineStoryQueryStrategy.USE_SUMMARY
        elif user_str == "match-on-both":
            return HeadlineStoryQueryStrategy.USE_TITLE_AND_SUMMARY
        else:
            raise ValueError(
                f"Unrecognized user str for HeadlineStoryQueryStrategy: {user_str}"
            )


TokenLogprob = Tuple[str, float]
RelevancyScoredHeadline = Tuple[Headline, float]
