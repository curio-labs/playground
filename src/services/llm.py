import json
import os

from openai import OpenAI
from pydantic import BaseModel

from .tables import get_stories
from .utils import execute_in_thread_pool, TaskList

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
    id: str
    title: str
    value: float


def make_llm_request_for_story_batch(stories, prompt: str, limit=10):
    # remove publication date from stories
    content = [
        {
            "id": str(story.id),
            "title": story.title,
            "text": story.text,
        }
        for story in stories
    ]
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
    return result


def make_llm_request_for_single_story(story, prompt: str):
    content = {
        "id": str(story.id),
        "title": story.title,
        "text": story.text,
    }
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
    return result


def make_concurrent_llm_requests_for_stories(prompt: str, stories: list[Story]):
    tasks: TaskList = [
        (
            make_llm_request_for_single_story,
            (
                story,
                prompt,
            ),
        )
        for story in stories
    ]
    results = execute_in_thread_pool(tasks, max_workers=10)
    results = sorted(results, key=lambda x: x["value"], reverse=True)
    return results
