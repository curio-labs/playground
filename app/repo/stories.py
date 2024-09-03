import random

from app import models as md
from src import services


def get_repeat_stories(story_ids):
    stories = services.get_stories_by_id(story_ids=story_ids)
    stories = [
        md.Story(
            id=story["id"],
            title=story["title"],
            text=story["text"],
            published_at=story["published_at"],
            publication=story["publication"],
            author=story["author"],
            type=story["type"],
            classification=story["classification"],
        )
        for story in stories["data"]
    ]
    return stories


def get_random_stories(
    limit=20,
    is_vector_search=False,
    vector_search=None,
    query=None,
    start_date=None,
):
    if is_vector_search:
        if query is None or start_date is None:
            raise ValueError(
                "Query and Start Date must be provided when vector_search is True."
            )
        vector_stories = services.get_vector_search_stories(
            start_date=start_date,
            limit=1_000,
            vector_search=vector_search,
        )
        story_ids = [story["id"] for story in vector_stories]
        stories = services.get_stories_by_id(story_ids=story_ids)["data"]
        for story in stories:
            story["similarity_score"] = next(
                item["similarity_score"]
                for item in vector_stories
                if item["id"] == story["id"]
            )
        random.shuffle(stories)
        stories = sorted(
            stories[:limit], key=lambda x: x["similarity_score"], reverse=True
        )

    else:
        stories = services.get_stories(limit=1_000, start_date=start_date)["data"]
        random.shuffle(stories)
    return [
        md.Story(
            id=story["id"],
            title=story["title"],
            text=story["text"],
            published_at=story["published_at"],
            publication=story["publication"],
            author=story["author"],
            type=story["type"],
            classification=story["classification"],
            similarity_score=round(story.get("similarity_score", 0), 2),
        )
        for story in stories
    ]
