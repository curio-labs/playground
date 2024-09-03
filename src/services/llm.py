import datetime
import json
import os
from typing import Optional

from openai import OpenAI
from pydantic import BaseModel

from .utils import TaskList, execute_in_thread_pool

OPEN_AI_DEFAULT_MODEL = "gpt-4o-2024-08-06"
OPEN_AI_API_URL = "https://api.openai.com/v1/chat/completions"
OPEN_AI_API_KEY = os.environ["OPENAI_API_KEY"]

client = OpenAI()


class Story(BaseModel):
    id: str
    title: str


class LLMMultiStoryResponse(BaseModel):
    stories: list[Story]


class LLMSingleStoryValueResponse(BaseModel):
    value: float


def make_llm_request_for_story_batch(stories, prompt: str, limit=10):
    # remove publication date from stories
    story_llm_ids_lookup = {}
    content = []
    for idx, story in enumerate(stories):
        story_llm_ids_lookup[idx] = story.id
        data = {
            "id": idx,
            "title": story.title,
            "text": story.text,
        }
        content.append(data)
    result = client.beta.chat.completions.parse(
        model=OPEN_AI_DEFAULT_MODEL,
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": json.dumps(content)},
        ],
        response_format=LLMMultiStoryResponse,
    )

    result = result.choices[0].message.parsed.json()
    result = json.loads(result)
    stories = result["stories"]
    for story in stories:
        idx = story["id"]
        story["id"] = story_llm_ids_lookup[int(idx)]
    return stories


def make_llm_request_for_single_story(story, prompt: str, attributes):
    content = {}

    for attribute in attributes:
        value = getattr(story, attribute, None)
        if isinstance(value, datetime.datetime):
            content[attribute] = value.isoformat()
        else:
            content[attribute] = value

    result = client.beta.chat.completions.parse(
        model=OPEN_AI_DEFAULT_MODEL,
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": json.dumps(content)},
        ],
        response_format=LLMSingleStoryValueResponse,
    )

    result = result.choices[0].message.parsed.json()
    result = json.loads(result)
    result["id"] = story.id
    result["title"] = story.title
    result["value"] = result["value"] if result["value"] is not None else 0
    return result


def make_concurrent_llm_requests_for_stories(
    prompt: str, stories: list[Story], attributes: Optional[list[str]] = None
):
    tasks: TaskList = [
        (
            make_llm_request_for_single_story,
            (
                story,
                prompt,
                attributes,
            ),
        )
        for story in stories
    ]
    results = execute_in_thread_pool(tasks, max_workers=10)
    results = sorted(results, key=lambda x: x["value"], reverse=True)
    return results
